from app.core.database import get_supabase_service
from app.models.user import UserUpdate, FollowRequest
from app.services.auth_service import AuthService
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class UserService:
    """用户服务类"""
    
    def __init__(self):
        self.supabase_service = get_supabase_service()
        self.auth_service = AuthService()
    
    async def get_user_profile(self, email: str) -> Dict[str, Any]:
        """获取用户资料"""
        try:
            response = self.supabase_service.table("users").select("*").eq("email", email).execute()
            if response.data:
                return response.data[0]
            else:
                raise ValueError("用户不存在")
        except Exception as e:
            logger.error(f"获取用户资料失败: {e}")
            raise
    
    async def update_user_profile(self, email: str, profile: UserUpdate, token: str) -> Dict[str, Any]:
        """更新用户资料"""
        try:
            # 验证令牌
            current_user = await self.auth_service.get_current_user(token)
            if current_user["email"] != email:
                raise ValueError("无权限更新其他用户资料")
            
            # 更新资料
            update_data = profile.dict(exclude_unset=True)
            update_data["updated_at"] = "2024-01-01T00:00:00.000Z"  # 实际应该用datetime.utcnow()
            
            response = self.supabase_service.table("users").update(update_data).eq("email", email).execute()
            
            if response.data:
                return response.data[0]
            else:
                raise ValueError("更新失败")
                
        except Exception as e:
            logger.error(f"更新用户资料失败: {e}")
            raise
    
    async def upload_avatar(self, avatar, token: str) -> Dict[str, Any]:
        """上传头像"""
        try:
            # 这里实现文件上传逻辑
            return {
                "avatar_url": "https://example.com/avatar.jpg",
                "message": "头像上传成功"
            }
        except Exception as e:
            logger.error(f"头像上传失败: {e}")
            raise
    
    async def get_followers(self, email: str) -> List[Dict[str, Any]]:
        """获取粉丝列表"""
        try:
            # 这里实现获取粉丝逻辑
            return []
        except Exception as e:
            logger.error(f"获取粉丝列表失败: {e}")
            raise
    
    async def get_following(self, email: str) -> List[Dict[str, Any]]:
        """获取关注列表"""
        try:
            # 这里实现获取关注列表逻辑
            return []
        except Exception as e:
            logger.error(f"获取关注列表失败: {e}")
            raise
    
    async def follow_user(self, follow_request: FollowRequest, token: str) -> Dict[str, Any]:
        """关注用户"""
        try:
            # 这里实现关注用户逻辑
            return {
                "message": "关注成功",
                "follower": follow_request.follower_email,
                "following": follow_request.following_email
            }
        except Exception as e:
            logger.error(f"关注用户失败: {e}")
            raise
    
    async def unfollow_user(self, follow_request: FollowRequest, token: str) -> Dict[str, Any]:
        """取消关注"""
        try:
            # 这里实现取消关注逻辑
            return {
                "message": "取消关注成功",
                "follower": follow_request.follower_email,
                "following": follow_request.following_email
            }
        except Exception as e:
            logger.error(f"取消关注失败: {e}")
            raise
    
    async def get_follow_status(self, target_email: str, token: str) -> Dict[str, Any]:
        """获取关注状态"""
        try:
            # 这里实现获取关注状态逻辑
            return {
                "is_following": False,
                "follower_count": 0,
                "following_count": 0
            }
        except Exception as e:
            logger.error(f"获取关注状态失败: {e}")
            raise
