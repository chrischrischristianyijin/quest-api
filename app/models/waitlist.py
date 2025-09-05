from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class WaitlistBase(BaseModel):
    email: EmailStr

class WaitlistCreate(WaitlistBase):
    """创建等待列表条目"""
    pass

class WaitlistResponse(BaseModel):
    """等待列表条目响应"""
    id: str
    email: str
    created_at: datetime
    status: str = "active"  # active, unsubscribed, notified
    source: Optional[str] = "website"  # website, extension, referral, etc.
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class WaitlistUpdate(BaseModel):
    """更新等待列表条目"""
    status: Optional[str] = None
    source: Optional[str] = None

class WaitlistStats(BaseModel):
    """等待列表统计"""
    total_emails: int
    active_emails: int
    unsubscribed_emails: int
    notified_emails: int
    recent_signups: int  # 最近7天注册数
