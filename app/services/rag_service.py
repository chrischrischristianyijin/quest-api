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
                    try:
                        # 处理PostgreSQL vector(1536)类型数据
                        embedding_data = self._normalize_embedding_data(item['embedding'], item['id'])
                        
                        if embedding_data is None:
                            continue  # 跳过无效的embedding数据
                        
                        # 计算余弦相似度
                        similarity = self._calculate_cosine_similarity(query_embedding, embedding_data)
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
                            
                    except Exception as e:
                        logger.warning(f"处理embedding失败: {item['id']}, 错误: {e}")
                        continue
            
            # 按相似度排序并取前k个
            chunks_with_scores.sort(key=lambda x: x.score, reverse=True)
            top_chunks = chunks_with_scores[:k]
            
            logger.info(f"备用方法检索到 {len(top_chunks)} 个相关分块（相似度 >= {min_score}）")
            return top_chunks
            
        except Exception as e:
            logger.error(f"备用检索方法失败: {e}")
            raise
    
    def _normalize_embedding_data(self, embedding_data: Any, chunk_id: str) -> Optional[List[float]]:
        """标准化embedding数据，处理PostgreSQL vector(1536)类型"""
        try:
            # 如果已经是列表，直接检查
            if isinstance(embedding_data, list):
                if len(embedding_data) == self.embedding_dimensions:
                    # 确保所有元素都是数值类型
                    try:
                        return [float(x) for x in embedding_data]
                    except (ValueError, TypeError):
                        logger.warning(f"embedding列表包含非数值元素: {chunk_id}")
                        return None
                else:
                    logger.warning(f"embedding维度错误: {chunk_id}, 期望{self.embedding_dimensions}, 实际{len(embedding_data)}")
                    return None
            
            # 如果是字符串，尝试解析
            elif isinstance(embedding_data, str):
                try:
                    # 尝试解析为Python列表
                    parsed_data = eval(embedding_data)
                    if isinstance(parsed_data, list) and len(parsed_data) == self.embedding_dimensions:
                        return [float(x) for x in parsed_data]
                    else:
                        logger.warning(f"解析的embedding格式错误: {chunk_id}")
                        return None
                except Exception as e:
                    logger.warning(f"无法解析embedding字符串: {chunk_id}, 错误: {e}")
                    return None
            
            # 如果是numpy数组
            elif hasattr(embedding_data, 'tolist'):
                try:
                    data_list = embedding_data.tolist()
                    if len(data_list) == self.embedding_dimensions:
                        return [float(x) for x in data_list]
                    else:
                        logger.warning(f"numpy数组维度错误: {chunk_id}")
                        return None
                except Exception as e:
                    logger.warning(f"转换numpy数组失败: {chunk_id}, 错误: {e}")
                    return None
            
            # 如果是元组
            elif isinstance(embedding_data, tuple):
                if len(embedding_data) == self.embedding_dimensions:
                    try:
                        return [float(x) for x in embedding_data]
                    except (ValueError, TypeError):
                        logger.warning(f"embedding元组包含非数值元素: {chunk_id}")
                        return None
                else:
                    logger.warning(f"embedding元组维度错误: {chunk_id}")
                    return None
            
            else:
                logger.warning(f"未知的embedding数据类型: {chunk_id}, 类型: {type(embedding_data)}")
                return None
                
        except Exception as e:
            logger.error(f"标准化embedding数据失败: {chunk_id}, 错误: {e}")
            return None

    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度（输入已通过_normalize_embedding_data标准化）"""
        try:
            import numpy as np
            
            # 转换为numpy数组，确保数据类型为float64
            a = np.array(vec1, dtype=np.float64)
            b = np.array(vec2, dtype=np.float64)
            
            # 检查维度是否匹配
            if len(a) != len(b):
                logger.warning(f"向量维度不匹配: {len(a)} vs {len(b)}")
                return 0.0
            
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
