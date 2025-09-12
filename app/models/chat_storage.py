from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MemoryType(str, Enum):
    """记忆类型枚举"""
    USER_PREFERENCE = "user_preference"  # 用户偏好
    FACT = "fact"  # 事实信息
    CONTEXT = "context"  # 上下文信息
    INSIGHT = "insight"  # 洞察信息

# 基础模型
class ChatSessionBase(BaseModel):
    """聊天会话基础模型"""
    user_id: UUID = Field(..., description="用户ID")
    title: Optional[str] = Field(None, description="会话标题")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")

class ChatSessionCreate(ChatSessionBase):
    """创建聊天会话"""
    pass

class ChatSessionUpdate(BaseModel):
    """更新聊天会话"""
    title: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatSession(ChatSessionBase):
    """聊天会话模型"""
    id: UUID = Field(..., description="会话ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    is_active: bool = Field(True, description="是否活跃")
    
    class Config:
        from_attributes = True

# 消息模型
class ChatMessageBase(BaseModel):
    """聊天消息基础模型"""
    session_id: UUID = Field(..., description="会话ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    parent_message_id: Optional[UUID] = Field(None, description="父消息ID")

class ChatMessageCreate(ChatMessageBase):
    """创建聊天消息"""
    pass

class ChatMessage(ChatMessageBase):
    """聊天消息模型"""
    id: UUID = Field(..., description="消息ID")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True

# RAG上下文模型
class RAGChunkInfo(BaseModel):
    """RAG分块信息"""
    id: str = Field(..., description="分块ID")
    insight_id: str = Field(..., description="见解ID")
    chunk_index: int = Field(..., description="分块索引")
    chunk_text: str = Field(..., description="分块文本")
    chunk_size: int = Field(..., description="分块大小")
    score: float = Field(..., description="相似度分数")
    created_at: str = Field(..., description="创建时间")

class ChatRAGContextBase(BaseModel):
    """RAG上下文基础模型"""
    message_id: UUID = Field(..., description="消息ID")
    rag_chunks: List[RAGChunkInfo] = Field(..., description="RAG分块列表")
    context_text: Optional[str] = Field(None, description="格式化上下文文本")
    total_context_tokens: int = Field(0, description="上下文总token数")
    extracted_keywords: Optional[str] = Field(None, description="提取的关键词")
    rag_k: int = Field(10, description="RAG检索数量")
    rag_min_score: float = Field(0.25, description="RAG最小相似度")

class ChatRAGContextCreate(ChatRAGContextBase):
    """创建RAG上下文"""
    pass

class ChatRAGContext(ChatRAGContextBase):
    """RAG上下文模型"""
    id: UUID = Field(..., description="上下文ID")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True

# 记忆模型
class ChatMemoryBase(BaseModel):
    """聊天记忆基础模型"""
    session_id: UUID = Field(..., description="会话ID")
    memory_type: MemoryType = Field(..., description="记忆类型")
    content: str = Field(..., description="记忆内容")
    importance_score: float = Field(0.5, ge=0, le=1, description="重要性分数")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")

class ChatMemoryCreate(ChatMemoryBase):
    """创建聊天记忆"""
    pass

class ChatMemoryUpdate(BaseModel):
    """更新聊天记忆"""
    content: Optional[str] = None
    importance_score: Optional[float] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatMemory(ChatMemoryBase):
    """聊天记忆模型"""
    id: UUID = Field(..., description="记忆ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    is_active: bool = Field(True, description="是否活跃")
    
    class Config:
        from_attributes = True

# 复合模型
class ChatSessionWithMessages(ChatSession):
    """包含消息的会话模型"""
    messages: List[ChatMessage] = Field(default_factory=list, description="消息列表")

class ChatMessageWithContext(ChatMessage):
    """包含RAG上下文的消息模型"""
    rag_context: Optional[ChatRAGContext] = Field(None, description="RAG上下文")

class ChatSessionOverview(BaseModel):
    """会话概览模型"""
    id: UUID = Field(..., description="会话ID")
    user_id: UUID = Field(..., description="用户ID")
    title: Optional[str] = Field(None, description="会话标题")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    is_active: bool = Field(True, description="是否活跃")
    message_count: int = Field(0, description="消息数量")
    last_message_at: Optional[datetime] = Field(None, description="最后消息时间")

# 请求/响应模型
class ChatSessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: List[ChatSessionOverview] = Field(..., description="会话列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="页码")
    size: int = Field(..., description="页大小")

class ChatContextResponse(BaseModel):
    """聊天上下文响应"""
    session_id: UUID = Field(..., description="会话ID")
    messages: List[ChatMessageWithContext] = Field(..., description="消息列表")
    memories: List[ChatMemory] = Field(default_factory=list, description="记忆列表")
    total_tokens: int = Field(0, description="总token数")
