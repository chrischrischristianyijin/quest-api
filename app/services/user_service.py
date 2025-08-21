from app.models.user import UserUpdate
from app.core.database import get_supabase_service
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        self.supabase_service = get_supabase_service()

    async def update_user_profile(self, user_id: str, user_update: UserUpdate) -> Dict[str, Any]:
        """更新用户资料"""
        try:
            # 更新profiles表
            update_data = {}
            if user_update.nickname is not None:
                update_data['nickname'] = user_update.nickname
            if user_update.avatar_url is not None:
                update_data['avatar_url'] = user_update.avatar_url
            if user_update.bio is not None:
                update_data['bio'] = user_update.bio

            if update_data:
                response = self.supabase_service.table('profiles').update(update_data).eq('id', user_id).execute()
                if response.data:
                    logger.info(f"用户资料更新成功: {user_id}")
                    return {"success": True, "data": response.data[0]}
                else:
                    raise ValueError("用户资料更新失败")
            else:
                return {"success": True, "message": "无需更新"}
        except Exception as e:
            logger.error(f"更新用户资料失败: {e}")
            raise ValueError(f"更新用户资料失败: {e}")

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户资料"""
        try:
            response = self.supabase_service.table('profiles').select('*').eq('id', user_id).execute()
            if response.data:
                return {"success": True, "data": response.data[0]}
            else:
                raise ValueError("用户不存在")
        except Exception as e:
            logger.error(f"获取用户资料失败: {e}")
            raise ValueError(f"获取用户资料失败: {e}")

    async def upload_avatar(self, user_id: str, avatar_url: str) -> Dict[str, Any]:
        """上传用户头像"""
        try:
            response = self.supabase_service.table('profiles').update({'avatar_url': avatar_url}).eq('id', user_id).execute()
            if response.data:
                logger.info(f"用户头像更新成功: {user_id}")
                return {"success": True, "data": {"avatar_url": avatar_url}}
            else:
                raise ValueError("头像更新失败")
        except Exception as e:
            logger.error(f"上传头像失败: {e}")
            raise ValueError(f"上传头像失败: {e}")
