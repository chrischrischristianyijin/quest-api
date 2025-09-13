from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色: user, assistant, system")
    content: str = Field(..., description="消息内容")

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户问题")

class ChatResponse(BaseModel):
    """聊天响应模型"""
    success: bool = Field(True, description="请求是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")

class RAGChunk(BaseModel):
    """RAG检索到的分块数据"""
    id: UUID = Field(..., description="分块ID")
    insight_id: UUID = Field(..., description="见解ID")
    chunk_index: int = Field(..., description="分块索引")
    chunk_text: str = Field(..., description="分块文本")
    chunk_size: int = Field(..., description="分块大小")
    score: float = Field(..., description="相似度分数")
    created_at: datetime = Field(..., description="创建时间")
    # 新增insight相关信息
    insight_title: Optional[str] = Field(None, description="insight标题")
    insight_url: Optional[str] = Field(None, description="insight URL")
    insight_summary: Optional[str] = Field(None, description="insight摘要")

class RAGContext(BaseModel):
    """RAG上下文信息"""
    chunks: List[RAGChunk] = Field(..., description="检索到的分块")
    context_text: str = Field(..., description="格式化的上下文文本")
    total_tokens: int = Field(..., description="上下文总token数")

class ChatError(BaseModel):
    """聊天错误模型"""
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    request_id: Optional[str] = Field(None, description="请求ID")
