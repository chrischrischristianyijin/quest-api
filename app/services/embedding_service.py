"""
OpenAI Embedding 服务
用于生成文本的向量表示，支持相似度搜索
"""

import logging
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# 检查 OpenAI 是否可用
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI 库不可用，将使用模拟实现")


@dataclass
class EmbeddingConfig:
    """Embedding 配置"""
    enabled: bool = True
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    batch_size: int = 100
    max_retries: int = 3
    timeout: int = 30
    api_key: Optional[str] = None


class EmbeddingService:
    """OpenAI Embedding 服务"""
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or self._get_default_config()
        self.client = None
        self._initialize_client()
    
    def _get_default_config(self) -> EmbeddingConfig:
        """获取默认配置"""
        return EmbeddingConfig(
            enabled=os.getenv('EMBEDDING_ENABLED', 'true').lower() == 'true',
            model=os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small'),
            dimensions=int(os.getenv('OPENAI_EMBEDDING_DIMENSIONS', '1536')),
            batch_size=int(os.getenv('OPENAI_EMBEDDING_BATCH_SIZE', '100')),
            max_retries=int(os.getenv('OPENAI_EMBEDDING_MAX_RETRIES', '3')),
            timeout=int(os.getenv('OPENAI_EMBEDDING_TIMEOUT', '30')),
            api_key=os.getenv('OPENAI_API_KEY')
        )
    
    def _initialize_client(self):
        """初始化 OpenAI 客户端"""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI 库不可用，embedding 功能将被禁用")
            return
        
        if not self.config.api_key:
            logger.warning("OpenAI API Key 未配置，embedding 功能将被禁用")
            return
        
        try:
            self.client = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                timeout=self.config.timeout
            )
            logger.info(f"OpenAI Embedding 客户端初始化成功，模型: {self.config.model}")
        except Exception as e:
            logger.error(f"OpenAI 客户端初始化失败: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """检查 embedding 服务是否可用"""
        return (
            OPENAI_AVAILABLE and 
            self.config.enabled and 
            self.config.api_key and 
            self.client is not None
        )
    
    async def generate_single_embedding(self, text: str) -> Optional[Dict[str, Any]]:
        """
        生成单个文本的 embedding
        
        Args:
            text: 输入文本
        
        Returns:
            包含 embedding 信息的字典，失败时返回 None
        """
        if not self.is_available():
            logger.warning("Embedding 服务不可用")
            return None
        
        if not text or not text.strip():
            logger.warning("输入文本为空")
            return None
        
        try:
            # 清理文本
            cleaned_text = text.strip()
            
            # 调用 OpenAI API
            response = await self.client.embeddings.create(
                model=self.config.model,
                input=cleaned_text,
                dimensions=self.config.dimensions
            )
            
            embedding = response.data[0].embedding
            tokens_used = response.usage.total_tokens
            
            logger.debug(f"成功生成 embedding，文本长度: {len(cleaned_text)}, tokens: {tokens_used}")
            
            return {
                'embedding': embedding,
                'model': self.config.model,
                'dimensions': len(embedding),
                'tokens_used': tokens_used,
                'text_length': len(cleaned_text),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成单个 embedding 失败: {e}")
            return None
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[Optional[Dict[str, Any]]]:
        """
        批量生成 embedding
        
        Args:
            texts: 文本列表
        
        Returns:
            embedding 信息列表，失败的项目为 None
        """
        if not self.is_available():
            logger.warning("Embedding 服务不可用")
            return [None] * len(texts)
        
        if not texts:
            return []
        
        # 过滤空文本
        valid_texts = [(i, text.strip()) for i, text in enumerate(texts) if text and text.strip()]
        if not valid_texts:
            logger.warning("没有有效的文本")
            return [None] * len(texts)
        
        results = [None] * len(texts)
        
        try:
            # 分批处理
            for batch_start in range(0, len(valid_texts), self.config.batch_size):
                batch_end = min(batch_start + self.config.batch_size, len(valid_texts))
                batch_texts = [text for _, text in valid_texts[batch_start:batch_end]]
                batch_indices = [i for i, _ in valid_texts[batch_start:batch_end]]
                
                # 调用 OpenAI API
                response = await self.client.embeddings.create(
                    model=self.config.model,
                    input=batch_texts,
                    dimensions=self.config.dimensions
                )
                
                # 处理结果
                for i, embedding_data in enumerate(response.data):
                    original_index = batch_indices[i]
                    results[original_index] = {
                        'embedding': embedding_data.embedding,
                        'model': self.config.model,
                        'dimensions': len(embedding_data.embedding),
                        'tokens_used': response.usage.total_tokens // len(batch_texts),
                        'text_length': len(batch_texts[i]),
                        'generated_at': datetime.now().isoformat()
                    }
                
                logger.debug(f"批量生成 embedding 完成: {batch_start}-{batch_end-1}")
                
                # 避免 API 限制
                if batch_end < len(valid_texts):
                    await asyncio.sleep(0.1)
            
            success_count = sum(1 for r in results if r is not None)
            logger.info(f"批量生成 embedding 完成: {success_count}/{len(texts)} 成功")
            
            return results
            
        except Exception as e:
            logger.error(f"批量生成 embedding 失败: {e}")
            return [None] * len(texts)
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        计算两个 embedding 的余弦相似度
        
        Args:
            embedding1: 第一个 embedding
            embedding2: 第二个 embedding
        
        Returns:
            相似度分数 (0-1)
        """
        try:
            # 转换为 numpy 数组
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # 计算余弦相似度
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"计算相似度失败: {e}")
            return 0.0
    
    def calculate_distance(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        计算两个 embedding 的欧几里得距离
        
        Args:
            embedding1: 第一个 embedding
            embedding2: 第二个 embedding
        
        Returns:
            距离值（越小越相似）
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            distance = np.linalg.norm(vec1 - vec2)
            return float(distance)
            
        except Exception as e:
            logger.error(f"计算距离失败: {e}")
            return float('inf')


# 全局 embedding 服务实例
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """获取全局 embedding 服务实例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

def is_embedding_enabled() -> bool:
    """检查 embedding 功能是否启用"""
    service = get_embedding_service()
    return service.is_available()

async def generate_chunk_embeddings(chunks: List[str]) -> List[Optional[Dict[str, Any]]]:
    """
    为分块文本生成 embedding
    
    Args:
        chunks: 分块文本列表
    
    Returns:
        embedding 信息列表
    """
    service = get_embedding_service()
    return await service.generate_batch_embeddings(chunks)

async def generate_single_embedding(text: str) -> Optional[Dict[str, Any]]:
    """
    为单个文本生成 embedding
    
    Args:
        text: 输入文本
    
    Returns:
        embedding 信息
    """
    service = get_embedding_service()
    return await service.generate_single_embedding(text)
