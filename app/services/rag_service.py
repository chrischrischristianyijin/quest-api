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
        min_score: float = 0.15,
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
        min_score: float = 0.15,
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
                    return self._process_hnsw_results(response.data, k)
                else:
                    logger.info("HNSW向量搜索没有找到结果")
                    return []
                    
            except Exception as vector_error:
                logger.warning(f"HNSW向量搜索失败: {vector_error}")
                return []
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            raise
    
    def _process_hnsw_results(self, results: List[Dict], k: int) -> List[RAGChunk]:
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
            
            if filtered_chunks:
                avg_score = sum(chunk.score for chunk in filtered_chunks) / len(filtered_chunks)
                logger.info(f"HNSW检索到 {len(filtered_chunks)} 个相关分块（平均相似度: {avg_score:.3f}）")
            
            return filtered_chunks
            
        except Exception as e:
            logger.error(f"处理HNSW结果失败: {e}")
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
        """个性化检索策略"""
        try:
            # 基础检索
            chunks = await self.retrieve_chunks(
                query_embedding=query_embedding,
                user_id=user_id,
                k=k,
                min_score=min_score,
                query_text=query_text
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
