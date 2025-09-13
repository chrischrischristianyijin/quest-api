from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class UserBase(BaseModel):
    email: EmailStr
    nickname: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserMemoryProfile(BaseModel):
    """用户记忆档案"""
    preferences: Dict[str, Any] = {}  # 用户偏好
    facts: Dict[str, Any] = {}        # 重要事实
    context: Dict[str, Any] = {}      # 上下文信息
    insights: Dict[str, Any] = {}     # 洞察信息
    last_consolidated: Optional[datetime] = None  # 最后整合时间
    consolidation_settings: Dict[str, Any] = {    # 整合设置
        "auto_consolidate": True,
        "consolidation_threshold": 0.8,
        "max_memories_per_type": 50
    }

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    memory_profile: Optional[UserMemoryProfile] = None

class UserResponse(BaseModel):
    id: str
    email: str
    nickname: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class UserProfile(BaseModel):
    id: str
    email: str
    nickname: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    memory_profile: Optional[UserMemoryProfile] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class UserMemoryConsolidationRequest(BaseModel):
    """用户记忆整合请求"""
    memory_types: Optional[List[str]] = None  # 要整合的记忆类型，None表示所有类型
    force_consolidate: bool = False  # 是否强制整合
    consolidation_strategy: str = "similarity"  # 整合策略: similarity, importance, time
