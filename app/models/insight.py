from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class InsightBase(BaseModel):
    title: str
    description: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    tags: Optional[List[str]] = []

class InsightCreate(InsightBase):
    pass

class InsightUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    tags: Optional[List[str]] = None

class InsightResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    tags: List[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

class InsightListResponse(BaseModel):
    success: bool
    data: dict

# 用户标签相关模型
class UserTagBase(BaseModel):
    name: str
    color: str

class UserTagCreate(UserTagBase):
    pass

class UserTagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

class UserTagResponse(BaseModel):
    id: str
    user_id: str
    name: str
    color: str
    created_at: datetime
    updated_at: Optional[datetime] = None
