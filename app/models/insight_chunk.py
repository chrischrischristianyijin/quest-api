"""
Insight Chunk 数据模型
用于存储文本分块数据
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class InsightChunkBase(BaseModel):
    """Insight Chunk 基础模型"""
    insight_id: UUID = Field(..., description="关联的 insight ID")
    chunk_index: int = Field(..., ge=0, description="分块序号，从 0 开始")
    chunk_text: str = Field(..., min_length=1, description="分块文本内容")
    chunk_size: int = Field(..., ge=1, description="分块大小（字符数）")
    estimated_tokens: Optional[int] = Field(None, ge=0, description="预估 token 数")
    chunk_method: str = Field(default="recursive", description="分块方法")
    chunk_overlap: int = Field(default=200, ge=0, description="重叠大小")
    embedding: Optional[List[float]] = Field(None, description="文本向量表示")
    embedding_model: Optional[str] = Field(None, description="生成 embedding 的模型")
    embedding_tokens: Optional[int] = Field(None, ge=0, description="生成 embedding 消耗的 token 数")
    embedding_generated_at: Optional[datetime] = Field(None, description="embedding 生成时间")


class InsightChunkCreate(InsightChunkBase):
    """创建 Insight Chunk 的请求模型"""
    pass


class InsightChunkUpdate(BaseModel):
    """更新 Insight Chunk 的请求模型"""
    chunk_text: Optional[str] = Field(None, min_length=1, description="分块文本内容")
    chunk_size: Optional[int] = Field(None, ge=1, description="分块大小（字符数）")
    estimated_tokens: Optional[int] = Field(None, ge=0, description="预估 token 数")


class InsightChunk(InsightChunkBase):
    """Insight Chunk 响应模型"""
    id: UUID = Field(..., description="分块 ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class InsightChunkSummary(BaseModel):
    """Insight Chunk 摘要模型"""
    id: UUID = Field(..., description="分块 ID")
    insight_id: UUID = Field(..., description="关联的 insight ID")
    chunk_index: int = Field(..., description="分块序号")
    chunk_size: int = Field(..., description="分块大小（字符数）")
    estimated_tokens: Optional[int] = Field(None, description="预估 token 数")
    chunk_method: str = Field(..., description="分块方法")
    has_embedding: bool = Field(..., description="是否有 embedding")
    embedding_model: Optional[str] = Field(None, description="embedding 模型")
    preview: str = Field(..., description="文本预览（前100字符）")

    class Config:
        from_attributes = True


class InsightChunksResponse(BaseModel):
    """Insight Chunks 列表响应模型"""
    chunks: List[InsightChunkSummary] = Field(..., description="分块列表")
    total_chunks: int = Field(..., description="总分块数")
    total_size: int = Field(..., description="总字符数")
    total_tokens: Optional[int] = Field(None, description="总 token 数")
    chunk_method: str = Field(..., description="分块方法")
    avg_chunk_size: float = Field(..., description="平均分块大小")


class ChunkingResult(BaseModel):
    """分块结果模型"""
    chunks: List[str] = Field(..., description="分块文本列表")
    total_chunks: int = Field(..., description="总分块数")
    original_length: int = Field(..., description="原始文本长度")
    method: str = Field(..., description="分块方法")
    avg_chunk_size: float = Field(..., description="平均分块大小")
    compression_ratio: float = Field(..., description="压缩率")
    llm_optimized: bool = Field(default=False, description="是否 LLM 优化")
    estimated_tokens_per_chunk: int = Field(default=0, description="预估每块 token 数")


def create_chunk_summary(chunk: InsightChunk) -> InsightChunkSummary:
    """创建分块摘要"""
    return InsightChunkSummary(
        id=chunk.id,
        insight_id=chunk.insight_id,
        chunk_index=chunk.chunk_index,
        chunk_size=chunk.chunk_size,
        estimated_tokens=chunk.estimated_tokens,
        chunk_method=chunk.chunk_method,
        has_embedding=chunk.embedding is not None,
        embedding_model=chunk.embedding_model,
        preview=chunk.chunk_text[:100] + "..." if len(chunk.chunk_text) > 100 else chunk.chunk_text
    )


def create_chunks_response(chunks: List[InsightChunk]) -> InsightChunksResponse:
    """创建分块列表响应"""
    if not chunks:
        return InsightChunksResponse(
            chunks=[],
            total_chunks=0,
            total_size=0,
            total_tokens=None,
            chunk_method="unknown",
            avg_chunk_size=0.0
        )
    
    chunk_summaries = [create_chunk_summary(chunk) for chunk in chunks]
    total_size = sum(chunk.chunk_size for chunk in chunks)
    total_tokens = sum(chunk.estimated_tokens for chunk in chunks if chunk.estimated_tokens)
    avg_chunk_size = total_size / len(chunks) if chunks else 0.0
    
    return InsightChunksResponse(
        chunks=chunk_summaries,
        total_chunks=len(chunks),
        total_size=total_size,
        total_tokens=total_tokens,
        chunk_method=chunks[0].chunk_method if chunks else "unknown",
        avg_chunk_size=avg_chunk_size
    )
