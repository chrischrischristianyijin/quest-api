from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    nickname: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    nickname: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

class UserProfile(BaseModel):
    id: str
    email: str
    nickname: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
