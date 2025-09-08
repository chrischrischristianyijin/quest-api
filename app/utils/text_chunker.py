"""
文本分块器模块
基于 LangChain Splitters 实现高效的文本分块功能
"""

import logging
import re
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 检查 LangChain 是否可用
try:
    from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain 不可用，将使用自定义实现")


@dataclass
class ChunkConfig:
    """分块配置"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separators: List[str] = None
    length_function: callable = len
    keep_separator: bool = False
    add_start_index: bool = False
    strip_whitespace: bool = True
    
    def __post_init__(self):
        if self.separators is None:
            self.separators = ["\n\n", "\n", "。", "！", "？", "；", " ", ""]


class TextChunker:
    """文本分块器"""
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()
        self.langchain_available = LANGCHAIN_AVAILABLE
        
    def chunk_text(self, text: str, method: str = "recursive") -> Dict[str, Any]:
        """
        分块文本
        
        Args:
            text: 输入文本
            method: 分块方法 ("character" 或 "recursive")
        
        Returns:
            包含分块结果和统计信息的字典
        """
        if not text or not text.strip():
            return {
                "chunks": [],
                "total_chunks": 0,
                "original_length": 0,
                "method": method,
                "config": self.config.__dict__
            }
        
        try:
            if method == "character":
                chunks = self._chunk_with_character_splitter(text)
            elif method == "recursive":
                chunks = self._chunk_with_recursive_splitter(text)
            else:
                raise ValueError(f"不支持的分块方法: {method}")
            
            # 过滤空块
            chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
            
            return {
                "chunks": chunks,
                "total_chunks": len(chunks),
                "original_length": len(text),
                "method": method,
                "config": self.config.__dict__,
                "avg_chunk_size": sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0,
                "compression_ratio": len(text) / sum(len(chunk) for chunk in chunks) if chunks else 1.0
            }
            
        except Exception as e:
            logger.error(f"文本分块失败: {e}")
            return {
                "chunks": [text],
                "total_chunks": 1,
                "original_length": len(text),
                "method": method,
                "config": self.config.__dict__,
                "error": str(e)
            }
    
    def _chunk_with_character_splitter(self, text: str) -> List[str]:
        """使用 CharacterTextSplitter 分块"""
        if self.langchain_available:
            try:
                splitter = CharacterTextSplitter(
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap,
                    length_function=self.config.length_function,
                    add_start_index=self.config.add_start_index,
                    strip_whitespace=self.config.strip_whitespace
                )
                return splitter.split_text(text)
            except Exception as e:
                logger.warning(f"LangChain CharacterTextSplitter 失败，使用自定义实现: {e}")
        
        # 自定义实现
        return self._custom_character_split(text)
    
    def _chunk_with_recursive_splitter(self, text: str) -> List[str]:
        """使用 RecursiveCharacterTextSplitter 分块"""
        if self.langchain_available:
            try:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap,
                    separators=self.config.separators,
                    length_function=self.config.length_function,
                    keep_separator=self.config.keep_separator,
                    add_start_index=self.config.add_start_index,
                    strip_whitespace=self.config.strip_whitespace
                )
                return splitter.split_text(text)
            except Exception as e:
                logger.warning(f"LangChain RecursiveCharacterTextSplitter 失败，使用自定义实现: {e}")
        
        # 自定义实现
        return self._custom_recursive_split(text)
    
    def _custom_character_split(self, text: str) -> List[str]:
        """自定义字符级分块实现"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.config.chunk_size, len(text))
            
            # 尝试在单词边界分割
            if end < len(text):
                # 向前查找空格或标点
                for i in range(end, max(start + self.config.chunk_size // 2, start), -1):
                    if text[i] in [' ', '\n', '。', '！', '？', '；']:
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 计算下一个块的起始位置（考虑重叠）
            start = end - self.config.chunk_overlap
            if start < 0:
                start = end
        
        return chunks
    
    def _custom_recursive_split(self, text: str) -> List[str]:
        """自定义递归分块实现"""
        def _split_text_recursive(text: str, separators: List[str]) -> List[str]:
            if not text or len(text) <= self.config.chunk_size:
                return [text] if text.strip() else []
            
            # 尝试使用当前分隔符
            separator = separators[0] if separators else ""
            
            if separator:
                splits = text.split(separator)
                if len(splits) > 1:
                    chunks = []
                    current_chunk = ""
                    
                    for split in splits:
                        potential_chunk = current_chunk + split + separator if current_chunk else split
                        
                        if len(potential_chunk) <= self.config.chunk_size:
                            current_chunk = potential_chunk
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = split
                    
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    
                    # 递归处理过长的块
                    final_chunks = []
                    for chunk in chunks:
                        if len(chunk) > self.config.chunk_size:
                            final_chunks.extend(_split_text_recursive(chunk, separators[1:]))
                        else:
                            final_chunks.append(chunk)
                    
                    return final_chunks
            
            # 如果没有合适的分隔符，使用字符级分割
            return self._custom_character_split(text)
        
        return _split_text_recursive(text, self.config.separators)


def create_chunker(
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    method: str = "recursive",
    separators: Optional[List[str]] = None
) -> TextChunker:
    """
    创建文本分块器
    
    Args:
        chunk_size: 块大小
        chunk_overlap: 重叠大小
        method: 分块方法
        separators: 分隔符列表
    
    Returns:
        TextChunker 实例
    """
    config = ChunkConfig(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators
    )
    
    return TextChunker(config)


def chunk_text_for_llm(
    text: str,
    max_tokens: int = 4000,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    method: str = "recursive"
) -> Dict[str, Any]:
    """
    为 LLM 优化文本分块
    
    Args:
        text: 输入文本
        max_tokens: 最大 token 数
        chunk_size: 块大小
        chunk_overlap: 重叠大小
        method: 分块方法
    
    Returns:
        分块结果
    """
    # 根据 max_tokens 调整 chunk_size
    # 粗略估算：1 token ≈ 4 字符
    estimated_chunk_size = min(chunk_size, max_tokens * 4)
    
    chunker = create_chunker(
        chunk_size=estimated_chunk_size,
        chunk_overlap=chunk_overlap,
        method=method
    )
    
    result = chunker.chunk_text(text, method)
    
    # 添加 LLM 相关信息
    result["llm_optimized"] = True
    result["max_tokens"] = max_tokens
    result["estimated_tokens_per_chunk"] = estimated_chunk_size // 4
    
    return result


def is_langchain_available() -> bool:
    """检查 LangChain 是否可用"""
    return LANGCHAIN_AVAILABLE
