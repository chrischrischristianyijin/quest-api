from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class InsightBase(BaseModel):
    """Insight基础模型"""
    title: str = Field(..., min_length=1, max_length=200, description="见解标题")
    description: Optional[str] = Field(None, max_length=3000, description="见解描述")
    url: Optional[str] = Field(None, max_length=500, description="相关链接")
    image_url: Optional[str] = Field(None, max_length=500, description="图片地址")
    thought: Optional[str] = Field(None, max_length=2000, description="用户的想法/备注")

class InsightCreate(InsightBase):
    """创建Insight的请求模型"""
    tag_names: Optional[List[str]] = Field(None, description="标签名称列表，会自动创建或关联现有标签")

class InsightUpdate(BaseModel):
    """更新Insight的请求模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="见解标题")
    description: Optional[str] = Field(None, max_length=3000, description="见解描述")
    url: Optional[str] = Field(None, max_length=500, description="相关链接")
    image_url: Optional[str] = Field(None, max_length=500, description="图片地址")
    thought: Optional[str] = Field(None, max_length=2000, description="用户的想法/备注")
    tag_names: Optional[List[str]] = Field(None, description="标签名称列表，会替换现有标签")

class InsightResponse(InsightBase):
    """Insight响应模型"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    tags: List[dict] = Field(default_factory=list, description="标签信息列表")

class InsightListResponse(BaseModel):
    """Insight列表响应模型"""
    insights: List[InsightResponse]

# 用户标签模型
class UserTagBase(BaseModel):
    """用户标签基础模型"""
    name: str = Field(..., min_length=1, max_length=50, description="标签名称")
    color: str = Field(..., pattern=r'^#[0-9A-Fa-f]{6}$', description="标签颜色，十六进制格式")

class UserTagCreate(UserTagBase):
    """创建用户标签的请求模型"""
    pass

class UserTagUpdate(BaseModel):
    """更新用户标签的请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="标签名称")
    color: Optional[str] = Field(None, max_length=7, description="标签颜色，十六进制格式")

class UserTagResponse(UserTagBase):
    """用户标签响应模型"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
