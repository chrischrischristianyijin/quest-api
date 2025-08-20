from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    """用户基础模型"""
    email: EmailStr
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    """用户创建模型"""
    password: str

class UserUpdate(BaseModel):
    """用户更新模型"""
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(UserBase):
    """用户响应模型"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """用户登录模型"""
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    """用户资料模型"""
    id: str
    email: EmailStr
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class FollowRequest(BaseModel):
    """关注请求模型"""
    follower_email: EmailStr
    following_email: EmailStr

class FollowStatus(BaseModel):
    """关注状态模型"""
    is_following: bool
    follower_count: int
    following_count: int
