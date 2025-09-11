from typing import List, Optional, Dict, Any
import os
import logging
import httpx
import asyncio
from app.core.database import get_supabase_service
from app.models.chat import RAGChunk, RAGContext
from app.utils.summarize import estimate_tokens

logger = logging.getLogger(__name__)

class RAGService:
    """RAG检索服务"""
    
    def __init__(self):
        self.supabase = get_supabase_service()
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
        self.embedding_dimensions = int(os.getenv('OPENAI_EMBEDDING_DIMENSIONS', '1536'))
        
    async def embed_text(self, text: str) -> List[float]:
        """将文本转换为向量嵌入"""
        try:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY 未配置")
            
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'model': self.embedding_model,
                'input': text,
                'encoding_format': 'float'
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.openai_base_url}/embeddings",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                embedding = data['data'][0]['embedding']
                
                logger.info(f"文本嵌入成功，维度: {len(embedding)}")
                return embedding
                
        except Exception as e:
            logger.error(f"文本嵌入失败: {e}")
            raise
    
    async def retrieve_chunks(
        self, 
        query_embedding: List[float], 
        user_id: Optional[str] = None,
        k: int = 6, 
        min_score: float = 0.2,
        only_insight: Optional[str] = None
    ) -> List[RAGChunk]:
        """检索相关分块"""
        try:
            # 使用Python端相似度计算（简单可靠）
            return await self._fallback_retrieve_chunks(query_embedding, user_id, k, min_score, only_insight)
            
        except Exception as e:
            logger.error(f"分块检索失败: {e}")
            raise
    
    async def _fallback_retrieve_chunks(
        self, 
        query_embedding: List[float], 
        user_id: Optional[str] = None,
        k: int = 6, 
        min_score: float = 0.2,
        only_insight: Optional[str] = None
    ) -> List[RAGChunk]:
        """备用检索方法，使用Supabase API"""
        try:
            # 使用Supabase的PostgreSQL查询功能
            query = self.supabase.table('insight_chunks').select(
                'id, insight_id, chunk_index, chunk_text, chunk_size, created_at, embedding'
            ).not_.is_('embedding', 'null')
            
            # 添加用户过滤条件
            if user_id:
                # 先获取用户的insights
                insights_response = self.supabase.table('insights').select('id').eq('user_id', user_id).execute()
                if insights_response.data:
                    insight_ids = [insight['id'] for insight in insights_response.data]
                    query = query.in_('insight_id', insight_ids)
                else:
                    # 用户没有insights，返回空结果
                    return []
            
            # 添加insight过滤条件
            if only_insight:
                query = query.eq('insight_id', only_insight)
            
            # 执行查询
            response = query.execute()
            
            if not response.data:
                logger.warning("没有找到有embedding的分块")
                return []
            
            # 计算相似度并排序
            chunks_with_scores = []
            for item in response.data:
                if item['embedding']:
                    # 计算余弦相似度
                    similarity = self._calculate_cosine_similarity(query_embedding, item['embedding'])
                    if similarity >= min_score:
                        chunk = RAGChunk(
                            id=item['id'],
                            insight_id=item['insight_id'],
                            chunk_index=item['chunk_index'],
                            chunk_text=item['chunk_text'],
                            chunk_size=item['chunk_size'],
                            score=similarity,
                            created_at=item['created_at']
                        )
                        chunks_with_scores.append(chunk)
            
            # 按相似度排序并取前k个
            chunks_with_scores.sort(key=lambda x: x.score, reverse=True)
            top_chunks = chunks_with_scores[:k]
            
            logger.info(f"备用方法检索到 {len(top_chunks)} 个相关分块（相似度 >= {min_score}）")
            return top_chunks
            
        except Exception as e:
            logger.error(f"备用检索方法失败: {e}")
            raise
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        try:
            import numpy as np
            
            # 转换为numpy数组
            a = np.array(vec1)
            b = np.array(vec2)
            
            # 计算余弦相似度
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"计算余弦相似度失败: {e}")
            return 0.0
    
    
    def format_context(self, chunks: List[RAGChunk], max_tokens: int = 2000) -> RAGContext:
        """格式化检索到的分块为上下文"""
        try:
            if not chunks:
                return RAGContext(
                    chunks=[],
                    context_text="",
                    total_tokens=0
                )
            
            # 按分数排序（降序）
            sorted_chunks = sorted(chunks, key=lambda x: x.score, reverse=True)
            
            # 构建上下文文本
            context_parts = []
            total_tokens = 0
            
            for i, chunk in enumerate(sorted_chunks):
                # 格式化分块文本
                chunk_text = f"【{i+1} | {chunk.score:.2f}】{chunk.chunk_text}"
                chunk_tokens = estimate_tokens(chunk_text)
                
                # 检查是否超过token限制
                if total_tokens + chunk_tokens > max_tokens:
                    logger.info(f"上下文token限制 ({max_tokens})，停止添加更多分块")
                    break
                
                context_parts.append(chunk_text)
                total_tokens += chunk_tokens
            
            context_text = "\n\n".join(context_parts)
            
            logger.info(f"上下文格式化完成，包含 {len(context_parts)} 个分块，约 {total_tokens} tokens")
            
            return RAGContext(
                chunks=sorted_chunks[:len(context_parts)],
                context_text=context_text,
                total_tokens=total_tokens
            )
            
        except Exception as e:
            logger.error(f"上下文格式化失败: {e}")
            raise
    
    async def retrieve(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        k: int = 6, 
        min_score: float = 0.2,
        max_context_tokens: int = 2000
    ) -> RAGContext:
        """完整的RAG检索流程"""
        try:
            # 1. 文本嵌入
            query_embedding = await self.embed_text(query)
            
            # 2. 检索分块
            chunks = await self.retrieve_chunks(
                query_embedding=query_embedding,
                user_id=user_id,
                k=k,
                min_score=min_score
            )
            
            # 3. 格式化上下文
            context = self.format_context(chunks, max_context_tokens)
            
            return context
            
        except Exception as e:
            logger.error(f"RAG检索失败: {e}")
            raise
