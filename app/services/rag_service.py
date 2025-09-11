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
        min_score: float = 0.15,
        only_insight: Optional[str] = None
    ) -> List[RAGChunk]:
        """检索相关分块 - 支持多种检索策略"""
        try:
            # 策略1: 基础检索（只查询用户insights）
            chunks = await self._fallback_retrieve_chunks(query_embedding, user_id, k, min_score, only_insight)
            
            # 如果结果不足，尝试策略2: 降低阈值重新检索
            if len(chunks) < k and min_score > 0.1:
                logger.info(f"结果不足({len(chunks)}/{k})，降低阈值重新检索")
                chunks = await self._fallback_retrieve_chunks(query_embedding, user_id, k, 0.1, only_insight)
            
            # 策略3: 如果仍然不足，尝试增加k值
            if len(chunks) < k:
                logger.info(f"结果仍然不足({len(chunks)}/{k})，增加检索数量")
                chunks = await self._fallback_retrieve_chunks(query_embedding, user_id, k * 2, 0.05, only_insight)
                # 只取前k个
                chunks = chunks[:k]
            
            return chunks
            
        except Exception as e:
            logger.error(f"分块检索失败: {e}")
            raise
    
    async def _fallback_retrieve_chunks(
        self, 
        query_embedding: List[float], 
        user_id: Optional[str] = None,
        k: int = 10, 
        min_score: float = 0.15,
        only_insight: Optional[str] = None
    ) -> List[RAGChunk]:
        """优化的检索方法，优先查询用户相关的insights，无用户时提供公开数据"""
        try:
            # 如果没有提供user_id，尝试检索公开的insights作为回退
            if not user_id:
                logger.warning("未提供用户ID，尝试检索公开数据作为回退")
                return await self._retrieve_public_chunks(query_embedding, k, min_score, only_insight)
            
            # 1. 先获取用户的所有insights（包含更多元数据）
            insights_query = self.supabase.table('insights').select(
                'id, title, description, created_at, updated_at, tags'
            ).eq('user_id', user_id)
            
            insights_response = insights_query.execute()
            
            if not insights_response.data:
                logger.info(f"用户 {user_id} 没有insights")
                return []
            
            insight_ids = [insight['id'] for insight in insights_response.data]
            insights_map = {insight['id']: insight for insight in insights_response.data}
            
            logger.info(f"用户 {user_id} 有 {len(insight_ids)} 个insights")
            
            # 2. 查询这些insights的所有chunks
            chunks_query = self.supabase.table('insight_chunks').select(
                'id, insight_id, chunk_index, chunk_text, chunk_size, created_at, embedding'
            ).in_('insight_id', insight_ids).not_.is_('embedding', 'null')
            
            # 添加insight过滤条件
            if only_insight:
                chunks_query = chunks_query.eq('insight_id', only_insight)
            
            chunks_response = chunks_query.execute()
            
            if not chunks_response.data:
                logger.warning(f"用户 {user_id} 的insights中没有找到有embedding的分块")
                return []
            
            logger.info(f"找到 {len(chunks_response.data)} 个有embedding的分块")
            
            # 3. 计算相似度并排序（优化算法）
            chunks_with_scores = []
            for item in chunks_response.data:
                if item['embedding']:
                    try:
                        # 处理PostgreSQL vector(1536)类型数据
                        embedding_data = self._normalize_embedding_data(item['embedding'], item['id'])
                        
                        if embedding_data is None:
                            continue  # 跳过无效的embedding数据
                        
                        # 计算余弦相似度
                        similarity = self._calculate_cosine_similarity(query_embedding, embedding_data)
                        
                        # 应用相似度阈值
                        if similarity >= min_score:
                            # 获取insight元数据
                            insight_data = insights_map.get(item['insight_id'], {})
                            
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
            
            # 4. 按相似度排序并限制每个insight的chunks数量
            chunks_with_scores.sort(key=lambda x: x.score, reverse=True)
            
            # 限制每个insight的chunks数量，避免单一文章占主导
            max_chunks_per_insight = int(os.getenv('RAG_MAX_CHUNKS_PER_INSIGHT', '3'))
            insight_chunk_counts = {}
            filtered_chunks = []
            
            for chunk in chunks_with_scores:
                insight_id = chunk.insight_id
                current_count = insight_chunk_counts.get(insight_id, 0)
                
                if current_count < max_chunks_per_insight:
                    filtered_chunks.append(chunk)
                    insight_chunk_counts[insight_id] = current_count + 1
                    
                    # 如果已经达到总数量限制，停止
                    if len(filtered_chunks) >= k:
                        break
            
            top_chunks = filtered_chunks
            
            # 5. 记录检索统计信息
            if top_chunks:
                avg_score = sum(chunk.score for chunk in top_chunks) / len(top_chunks)
                logger.info(f"检索到 {len(top_chunks)} 个相关分块（相似度 >= {min_score}，平均相似度: {avg_score:.3f}）")
                
                # 记录来源insights分布
                source_insights = set(chunk.insight_id for chunk in top_chunks)
                insight_distribution = {}
                for chunk in top_chunks:
                    insight_id = chunk.insight_id
                    insight_distribution[insight_id] = insight_distribution.get(insight_id, 0) + 1
                
                logger.info(f"来源insights: {len(source_insights)} 个")
                logger.info(f"每个insight的chunks分布: {dict(list(insight_distribution.items())[:5])}")
            else:
                logger.info(f"没有找到相似度 >= {min_score} 的分块")
            
            return top_chunks
            
        except Exception as e:
            logger.error(f"检索用户insights失败: {e}")
            raise
    
    async def _retrieve_public_chunks(
        self,
        query_embedding: List[float],
        k: int = 10,
        min_score: float = 0.15,
        only_insight: Optional[str] = None
    ) -> List[RAGChunk]:
        """检索公开的insights作为回退机制"""
        try:
            logger.info("开始检索公开数据作为回退...")
            
            # 查询公开的insights（这里假设有一个is_public字段，如果没有则查询所有）
            # 注意：这里需要根据实际的数据库schema调整
            insights_query = self.supabase.table('insights').select(
                'id, title, description, created_at, updated_at, tags, user_id'
            )
            
            # 如果数据库中有is_public字段，可以添加过滤条件
            # insights_query = insights_query.eq('is_public', True)
            
            # 限制查询数量，避免查询过多数据
            insights_response = insights_query.limit(100).execute()
            
            if not insights_response.data:
                logger.info("没有找到公开的insights")
                return []
            
            insight_ids = [insight['id'] for insight in insights_response.data]
            insights_map = {insight['id']: insight for insight in insights_response.data}
            
            logger.info(f"找到 {len(insight_ids)} 个公开insights")
            
            # 查询这些insights的所有chunks
            chunks_query = self.supabase.table('insight_chunks').select(
                'id, insight_id, chunk_index, chunk_text, chunk_size, created_at, embedding'
            ).in_('insight_id', insight_ids).not_.is_('embedding', 'null')
            
            # 添加insight过滤条件
            if only_insight:
                chunks_query = chunks_query.eq('insight_id', only_insight)
            
            chunks_response = chunks_query.execute()
            
            if not chunks_response.data:
                logger.warning("公开insights中没有找到有embedding的分块")
                return []
            
            logger.info(f"找到 {len(chunks_response.data)} 个公开分块")
            
            # 计算相似度并排序
            chunks_with_scores = []
            for item in chunks_response.data:
                if item['embedding']:
                    try:
                        embedding_data = self._normalize_embedding_data(item['embedding'], item['id'])
                        if embedding_data is None:
                            continue
                        
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
                        logger.warning(f"处理公开chunk失败: {item['id']}, 错误: {e}")
                        continue
            
            # 按相似度排序并限制数量
            chunks_with_scores.sort(key=lambda x: x.score, reverse=True)
            
            # 限制每个insight的chunks数量，避免单一文章占主导
            max_chunks_per_insight = int(os.getenv('RAG_MAX_CHUNKS_PER_INSIGHT', '3'))
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
            
            if filtered_chunks:
                avg_score = sum(chunk.score for chunk in filtered_chunks) / len(filtered_chunks)
                logger.info(f"检索到 {len(filtered_chunks)} 个公开分块（相似度 >= {min_score}，平均相似度: {avg_score:.3f}）")
            else:
                logger.info(f"没有找到相似度 >= {min_score} 的公开分块")
            
            return filtered_chunks
            
        except Exception as e:
            logger.error(f"检索公开数据失败: {e}")
            return []
    
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
        k: int = 10, 
        min_score: float = 0.15,
        max_context_tokens: int = 4000
    ) -> RAGContext:
        """完整的RAG检索流程 - 支持个性化检索"""
        try:
            # 1. 文本嵌入
            query_embedding = await self.embed_text(query)
            
            # 2. 个性化检索策略
            chunks = await self._personalized_retrieve(
                query_embedding=query_embedding,
                query_text=query,
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
    
    async def _personalized_retrieve(
        self,
        query_embedding: List[float],
        query_text: str,
        user_id: Optional[str] = None,
        k: int = 10,
        min_score: float = 0.15
    ) -> List[RAGChunk]:
        """个性化检索策略"""
        try:
            # 基础检索
            chunks = await self.retrieve_chunks(
                query_embedding=query_embedding,
                user_id=user_id,
                k=k,
                min_score=min_score
            )
            
            # 如果用户有insights，尝试获取更多上下文
            if user_id and chunks:
                # 获取相关insights的更多chunks
                insight_ids = list(set(chunk.insight_id for chunk in chunks))
                if len(insight_ids) > 0:
                    # 为每个相关insight获取更多chunks
                    additional_chunks = await self._get_additional_chunks(
                        query_embedding, insight_ids, user_id, k // 2, min_score * 0.8
                    )
                    
                    # 合并并去重
                    all_chunks = chunks + additional_chunks
                    seen_ids = set()
                    unique_chunks = []
                    for chunk in all_chunks:
                        if chunk.id not in seen_ids:
                            unique_chunks.append(chunk)
                            seen_ids.add(chunk.id)
                    
                    # 重新排序并限制每个insight的chunks数量
                    unique_chunks.sort(key=lambda x: x.score, reverse=True)
                    
                    # 限制每个insight的chunks数量
                    max_chunks_per_insight = int(os.getenv('RAG_MAX_CHUNKS_PER_INSIGHT', '3'))
                    insight_chunk_counts = {}
                    filtered_chunks = []
                    
                    for chunk in unique_chunks:
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
    
    async def _get_additional_chunks(
        self,
        query_embedding: List[float],
        insight_ids: List[str],
        user_id: str,
        k: int,
        min_score: float
    ) -> List[RAGChunk]:
        """获取相关insights的额外chunks"""
        try:
            # 查询这些insights的所有chunks
            chunks_query = self.supabase.table('insight_chunks').select(
                'id, insight_id, chunk_index, chunk_text, chunk_size, created_at, embedding'
            ).in_('insight_id', insight_ids).not_.is_('embedding', 'null')
            
            chunks_response = chunks_query.execute()
            
            if not chunks_response.data:
                return []
            
            # 计算相似度
            chunks_with_scores = []
            for item in chunks_response.data:
                if item['embedding']:
                    try:
                        embedding_data = self._normalize_embedding_data(item['embedding'], item['id'])
                        if embedding_data is None:
                            continue
                        
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
                        logger.warning(f"处理额外chunk失败: {item['id']}, 错误: {e}")
                        continue
            
            # 排序并返回
            chunks_with_scores.sort(key=lambda x: x.score, reverse=True)
            return chunks_with_scores[:k]
            
        except Exception as e:
            logger.error(f"获取额外chunks失败: {e}")
            return []
