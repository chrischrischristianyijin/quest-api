from typing import List, Optional, Dict, Any
import os
import logging
import httpx
import asyncio
import numpy as np
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
        self.chat_model = os.getenv('CHAT_MODEL', 'gpt-4o-mini')
        
        
    async def extract_keywords(self, query: str) -> str:
        """使用大语言模型提取用户问题的关键词"""
        try:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY 未配置")
            
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json',
            }
            
            # 构建关键词提取提示
            keyword_prompt = (
                "Extract 2–5 abstracted keywords from the following user question for vector retrieval.\n"
                "Go beyond literal words if needed: include related concepts, entities, or topics that capture the intent behind the question.\n"
                "Keep them concise, specific, and semantically meaningful.\n"
                "Do not include filler words (e.g., \"how\", \"problem\", \"situation\").\n"
                "Keep the same language as the original question (Chinese → Chinese keywords, English → English keywords).\n"
                "Output only the keywords, separated by commas. No explanations, no numbering, no line breaks.\n\n"
                f"User question: {query}\n\n"
                "Keywords:"
            )
            
            # 根据模型类型设置不同的参数
            if 'gpt-5' in self.chat_model.lower():
                # GPT-5 mini 特殊参数
                payload = {
                    'model': self.chat_model,
                    'messages': [
                        {"role": "user", "content": keyword_prompt}
                    ],
                    'temperature': 0.1,
                    'max_completion_tokens': 100,  # GPT-5 mini 使用 max_completion_tokens
                    'verbosity': 'low',  # 简短回答
                    'reasoning_effort': 'minimal'  # 快速推理
                }
            else:
                # 标准 GPT 模型参数
                payload = {
                    'model': self.chat_model,
                    'messages': [
                        {"role": "user", "content": keyword_prompt}
                    ],
                    'temperature': 0.1,
                    'max_tokens': 100
                }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.openai_base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                keywords = data['choices'][0]['message']['content'].strip()
                
                logger.info(f"关键词提取成功: {keywords}")
                return keywords
                
        except Exception as e:
            logger.warning(f"关键词提取失败，使用原始问题: {e}")
            return query  # 失败时返回原始问题
        
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
        k: int = 10, 
        min_score: float = 0.25,
        only_insight: Optional[str] = None,
        query_text: str = ""
    ) -> List[RAGChunk]:
        """检索相关分块 - 支持多种检索策略"""
        try:
            # 基础检索（只查询用户insights）
            chunks = await self._fallback_retrieve_chunks(query_embedding, user_id, k, min_score, only_insight, query_text)
            
            return chunks
            
        except Exception as e:
            logger.error(f"分块检索失败: {e}")
            raise
    
    async def _fallback_retrieve_chunks(
        self, 
        query_embedding: List[float], 
        user_id: Optional[str] = None,
        k: int = 10, 
        min_score: float = 0.25,
        only_insight: Optional[str] = None,
        query_text: str = ""
    ) -> List[RAGChunk]:
        """使用Supabase HNSW向量搜索的检索方法"""
        try:
            # 必须提供user_id，只检索用户自己的insights
            if not user_id:
                logger.warning("未提供用户ID，无法检索用户相关数据")
                return []
            
            # 使用Supabase的原生HNSW向量搜索
            query_vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            logger.info(f"使用HNSW向量搜索，用户: {user_id}")
            
            # 使用向量搜索函数
            try:
                response = self.supabase.rpc('search_similar_chunks_by_vector', {
                    'query_embedding': query_vector_str,
                    'user_id_param': user_id,
                    'similarity_threshold': min_score,
                    'max_results': k * 5
                }).execute()
                
                if response.data:
                    logger.info(f"HNSW向量搜索找到 {len(response.data)} 个候选分块")
                    # 调试：显示第一个结果的结构
                    if response.data:
                        logger.debug(f"第一个结果的结构: {response.data[0]}")
                    return await self._process_hnsw_results(response.data, k)
                else:
                    logger.info("HNSW向量搜索没有找到结果")
                    return []
                    
            except Exception as vector_error:
                logger.warning(f"HNSW向量搜索失败: {vector_error}")
                return []
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            raise
    
    async def _process_hnsw_results(self, results: List[Dict], k: int) -> List[RAGChunk]:
        """处理HNSW搜索返回的结果"""
        try:
            chunks_with_scores = []
            for item in results:
                try:
                    # 假设HNSW结果包含similarity或distance字段
                    similarity = item.get('similarity', item.get('distance', 0.0))
                    
                    # 处理created_at字段，确保它是有效的日期时间
                    created_at = item.get('created_at', '')
                    if not created_at or created_at == '':
                        from datetime import datetime
                        created_at = datetime.utcnow().isoformat()
                    
                    chunk = RAGChunk(
                        id=item.get('chunk_id', item.get('id')),  # 支持两种字段名
                        insight_id=item['insight_id'],
                        chunk_index=item['chunk_index'],
                        chunk_text=item['chunk_text'],
                        chunk_size=item.get('chunk_size', len(item['chunk_text'])),
                        score=float(similarity),
                        created_at=created_at
                    )
                    chunks_with_scores.append(chunk)
                except Exception as e:
                    logger.warning(f"处理HNSW结果失败: {item.get('chunk_id', item.get('id', 'unknown'))}, 错误: {e}")
                    logger.debug(f"问题数据项: {item}")
                    continue
            
            # 按相似度排序
            chunks_with_scores.sort(key=lambda x: x.score, reverse=True)
            
            # 限制每个insight的chunks数量
            max_chunks_per_insight = int(os.getenv('RAG_MAX_CHUNKS_PER_INSIGHT', '5'))
            insight_chunk_counts = {}
            filtered_chunks = []
            
            for chunk in chunks_with_scores:
                insight_id = chunk.insight_id
                current_count = insight_chunk_counts.get(insight_id, 0)
                
                if current_count < max_chunks_per_insight:
                    filtered_chunks.append(chunk)
                    insight_chunk_counts[insight_id] = current_count + 1
                    
                    if len(filtered_chunks) >= k:
                        break
            
            # 获取insight信息并填充到chunks中
            if filtered_chunks:
                # 获取所有唯一的insight_id
                unique_insight_ids = list(set(str(chunk.insight_id) for chunk in filtered_chunks))
                
                # 批量获取insight信息
                insights_info = await self._get_insights_info(unique_insight_ids)
                
                # 为每个chunk填充insight信息
                for chunk in filtered_chunks:
                    insight_info = insights_info.get(str(chunk.insight_id), {})
                    chunk.insight_title = insight_info.get('title')
                    chunk.insight_url = insight_info.get('url')
                    chunk.insight_summary = insight_info.get('summary')
                
                avg_score = sum(chunk.score for chunk in filtered_chunks) / len(filtered_chunks)
                logger.info(f"HNSW检索到 {len(filtered_chunks)} 个相关分块（平均相似度: {avg_score:.3f}）")
            
            return filtered_chunks
            
        except Exception as e:
            logger.error(f"处理HNSW结果失败: {e}")
            return []
    
    async def _get_insights_info(self, insight_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量获取insight信息"""
        try:
            if not insight_ids:
                return {}
            
            # 构建查询条件
            query = self.supabase.table('insights').select('id, title, url, summary')
            
            # 使用in_查询来批量获取
            response = query.in_('id', insight_ids).execute()
            
            if response.data:
                # 构建insight_id到信息的映射
                insights_info = {}
                for insight in response.data:
                    insights_info[insight['id']] = {
                        'title': insight.get('title'),
                        'url': insight.get('url'),
                        'summary': insight.get('summary')
                    }
                
                logger.debug(f"成功获取 {len(insights_info)} 个insight的信息")
                return insights_info
            else:
                logger.warning("未找到任何insight信息")
                return {}
                
        except Exception as e:
            logger.error(f"获取insight信息失败: {e}")
            return {}
    
    def format_context(self, chunks: List[RAGChunk], max_tokens: int = 4000) -> RAGContext:
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
                # 构建增强的分块文本，包含insight信息
                chunk_parts = [f"【{i+1} | {chunk.score:.2f}】{chunk.chunk_text}"]
                
                # 添加insight标题（如果可用）
                if chunk.insight_title:
                    chunk_parts.append(f"来源标题: {chunk.insight_title}")
                
                # 添加insight URL（如果可用）
                if chunk.insight_url:
                    chunk_parts.append(f"来源链接: {chunk.insight_url}")
                
                # 添加insight summary（如果可用且不为空）
                if chunk.insight_summary and chunk.insight_summary.strip():
                    chunk_parts.append(f"内容摘要: {chunk.insight_summary}")
                
                chunk_text = "\n".join(chunk_parts)
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
        k: int = 10, 
        min_score: float = 0.25,
        max_context_tokens: int = 4000
    ) -> RAGContext:
        """完整的RAG检索流程 - 支持个性化检索"""
        try:
            # 1. 关键词提取
            logger.info(f"开始关键词提取 - 原始问题: {query}")
            keywords = await self.extract_keywords(query)
            logger.info(f"提取的关键词: {keywords}")
            
            # 2. 文本嵌入（使用关键词）
            query_embedding = await self.embed_text(keywords)
            
            # 3. 个性化检索策略
            chunks = await self._personalized_retrieve(
                query_embedding=query_embedding,
                query_text=query,  # 保留原始问题用于日志
                user_id=user_id,
                k=k,
                min_score=min_score
            )
            
            # 4. 格式化上下文
            context = self.format_context(chunks, max_context_tokens)
            
            return context
            
        except Exception as e:
            logger.error(f"RAG检索失败: {e}")
            raise
    
    async def _personalized_retrieve(
        self,
        query_embedding: List[float],
        query_text: str,
        user_id: Optional[str] = None,
        k: int = 10,
        min_score: float = 0.15
    ) -> List[RAGChunk]:
        """简化的个性化检索策略"""
        try:
            # 直接进行基础检索
            chunks = await self.retrieve_chunks(
                query_embedding=query_embedding,
                user_id=user_id,
                k=k,
                min_score=min_score,
                query_text=query_text
            )
            
            # 简单的去重和排序
            if chunks:
                # 按相似度排序
                chunks.sort(key=lambda x: x.score, reverse=True)
                
                # 限制每个insight的chunks数量（简化版）
                max_chunks_per_insight = int(os.getenv('RAG_MAX_CHUNKS_PER_INSIGHT', '3'))
                insight_chunk_counts = {}
                filtered_chunks = []
                
                for chunk in chunks:
                    insight_id = chunk.insight_id
                    current_count = insight_chunk_counts.get(insight_id, 0)
                    
                    if current_count < max_chunks_per_insight:
                        filtered_chunks.append(chunk)
                        insight_chunk_counts[insight_id] = current_count + 1
                        
                        # 如果已经达到总数量限制，停止
                        if len(filtered_chunks) >= k:
                            break
                
                chunks = filtered_chunks
            
            return chunks
            
        except Exception as e:
            logger.error(f"个性化检索失败: {e}")
            # 回退到基础检索
            return await self.retrieve_chunks(query_embedding, user_id, k, min_score)
    
