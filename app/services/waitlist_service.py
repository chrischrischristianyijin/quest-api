from app.core.database import get_supabase_service
from app.models.waitlist import WaitlistCreate, WaitlistResponse, WaitlistUpdate, WaitlistStats
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

class WaitlistService:
    def __init__(self):
        self.supabase = get_supabase_service()
    
    async def add_to_waitlist(
        self, 
        waitlist_data: WaitlistCreate, 
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """添加邮箱到等待列表"""
        try:
            # 检查邮箱是否已存在
            existing = await self.get_waitlist_by_email(waitlist_data.email)
            if existing:
                if existing["status"] == "active":
                    return {
                        "success": False,
                        "message": "Email already exists in waitlist",
                        "data": existing
                    }
                else:
                    # 如果之前退订了，重新激活
                    return await self.reactivate_waitlist(existing["id"])
            
            # 创建新的等待列表条目
            waitlist_entry = {
                "id": str(uuid.uuid4()),
                "email": waitlist_data.email,
                "status": "active",
                "source": "website",
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table('waitlist').insert(waitlist_entry).execute()
            
            if response.data:
                logger.info(f"Successfully added email to waitlist: {waitlist_data.email}")
                return {
                    "success": True,
                    "message": "Successfully added to waitlist",
                    "data": response.data[0]
                }
            else:
                raise Exception("Failed to insert waitlist entry")
                
        except Exception as e:
            logger.error(f"Error adding to waitlist: {e}")
            return {
                "success": False,
                "message": f"Failed to add to waitlist: {str(e)}"
            }
    
    async def get_waitlist_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """根据邮箱获取等待列表条目"""
        try:
            response = self.supabase.table('waitlist').select('*').eq('email', email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting waitlist by email: {e}")
            return None
    
    async def get_waitlist_by_id(self, waitlist_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取等待列表条目"""
        try:
            response = self.supabase.table('waitlist').select('*').eq('id', waitlist_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting waitlist by ID: {e}")
            return None
    
    async def update_waitlist(
        self, 
        waitlist_id: str, 
        update_data: WaitlistUpdate
    ) -> Dict[str, Any]:
        """更新等待列表条目"""
        try:
            update_dict = update_data.dict(exclude_unset=True)
            update_dict["updated_at"] = datetime.utcnow().isoformat()
            
            response = self.supabase.table('waitlist').update(update_dict).eq('id', waitlist_id).execute()
            
            if response.data:
                return {
                    "success": True,
                    "message": "Waitlist entry updated successfully",
                    "data": response.data[0]
                }
            else:
                return {
                    "success": False,
                    "message": "Waitlist entry not found"
                }
                
        except Exception as e:
            logger.error(f"Error updating waitlist: {e}")
            return {
                "success": False,
                "message": f"Failed to update waitlist: {str(e)}"
            }
    
    async def unsubscribe_waitlist(self, email: str) -> Dict[str, Any]:
        """退订等待列表"""
        try:
            waitlist_entry = await self.get_waitlist_by_email(email)
            if not waitlist_entry:
                return {
                    "success": False,
                    "message": "Email not found in waitlist"
                }
            
            return await self.update_waitlist(
                waitlist_entry["id"], 
                WaitlistUpdate(status="unsubscribed")
            )
            
        except Exception as e:
            logger.error(f"Error unsubscribing from waitlist: {e}")
            return {
                "success": False,
                "message": f"Failed to unsubscribe: {str(e)}"
            }
    
    async def reactivate_waitlist(self, waitlist_id: str) -> Dict[str, Any]:
        """重新激活等待列表条目"""
        return await self.update_waitlist(
            waitlist_id, 
            WaitlistUpdate(status="active")
        )
    
    async def get_waitlist_stats(self) -> Dict[str, Any]:
        """获取等待列表统计信息"""
        try:
            # 获取总数
            total_response = self.supabase.table('waitlist').select('id', count='exact').execute()
            total_emails = total_response.count or 0
            
            # 获取活跃用户数
            active_response = self.supabase.table('waitlist').select('id', count='exact').eq('status', 'active').execute()
            active_emails = active_response.count or 0
            
            # 获取退订用户数
            unsubscribed_response = self.supabase.table('waitlist').select('id', count='exact').eq('status', 'unsubscribed').execute()
            unsubscribed_emails = unsubscribed_response.count or 0
            
            # 获取已通知用户数
            notified_response = self.supabase.table('waitlist').select('id', count='exact').eq('status', 'notified').execute()
            notified_emails = notified_response.count or 0
            
            # 获取最近7天注册数
            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            recent_response = self.supabase.table('waitlist').select('id', count='exact').gte('created_at', seven_days_ago).execute()
            recent_signups = recent_response.count or 0
            
            stats = WaitlistStats(
                total_emails=total_emails,
                active_emails=active_emails,
                unsubscribed_emails=unsubscribed_emails,
                notified_emails=notified_emails,
                recent_signups=recent_signups
            )
            
            return {
                "success": True,
                "data": stats.dict()
            }
            
        except Exception as e:
            logger.error(f"Error getting waitlist stats: {e}")
            return {
                "success": False,
                "message": f"Failed to get waitlist stats: {str(e)}"
            }
    
    async def get_all_waitlist(
        self, 
        page: int = 1, 
        limit: int = 50, 
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取所有等待列表条目（分页）"""
        try:
            query = self.supabase.table('waitlist').select('*')
            
            if status:
                query = query.eq('status', status)
            
            # 计算偏移量
            offset = (page - 1) * limit
            
            # 获取数据
            response = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
            
            # 获取总数
            count_response = query.select('id', count='exact').execute()
            total = count_response.count or 0
            
            return {
                "success": True,
                "data": response.data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting all waitlist: {e}")
            return {
                "success": False,
                "message": f"Failed to get waitlist: {str(e)}"
            }
