from app.models.user import UserUpdate
from app.core.database import get_supabase_service
from typing import Dict, Any, Optional
import logging
import os

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

    async def upload_avatar_file(self, file_content: bytes, filename: str) -> str:
        """上传头像文件到Supabase Storage"""
        try:
            # 定义存储桶名称
            bucket_name = "avatars"
            
            # 上传文件到Supabase Storage
            logger.info(f"开始上传头像文件: {filename}")
            
            # 尝试上传文件
            upload_response = self.supabase_service.storage.from_(bucket_name).upload(
                path=filename,
                file=file_content,
                file_options={"content-type": "image/*"}
            )
            
            logger.info(f"文件上传响应: {upload_response}")
            
            # 获取公共URL
            public_url_response = self.supabase_service.storage.from_(bucket_name).get_public_url(filename)
            
            if public_url_response:
                avatar_url = public_url_response
                logger.info(f"头像文件上传成功: {avatar_url}")
                return avatar_url
            else:
                raise ValueError("获取文件公共URL失败")
                
        except Exception as e:
            logger.error(f"上传头像文件失败: {e}")
            # 如果是存储桶不存在的错误，尝试创建存储桶
            if "bucket" in str(e).lower() and "not found" in str(e).lower():
                logger.info("尝试创建avatars存储桶...")
                try:
                    # 创建存储桶
                    self.supabase_service.storage.create_bucket(bucket_name, {"public": True})
                    logger.info("avatars存储桶创建成功，重试上传...")
                    
                    # 重试上传
                    upload_response = self.supabase_service.storage.from_(bucket_name).upload(
                        path=filename,
                        file=file_content,
                        file_options={"content-type": "image/*"}
                    )
                    
                    public_url_response = self.supabase_service.storage.from_(bucket_name).get_public_url(filename)
                    if public_url_response:
                        avatar_url = public_url_response
                        logger.info(f"重试后头像文件上传成功: {avatar_url}")
                        return avatar_url
                    else:
                        raise ValueError("重试后获取文件公共URL失败")
                        
                except Exception as retry_error:
                    logger.error(f"创建存储桶或重试上传失败: {retry_error}")
                    raise ValueError(f"上传头像文件失败: {retry_error}")
            else:
                raise ValueError(f"上传头像文件失败: {e}")

    async def upload_avatar(self, user_id: str, avatar_url: str) -> Dict[str, Any]:
        """更新用户头像URL到数据库"""
        try:
            response = self.supabase_service.table('profiles').update({'avatar_url': avatar_url}).eq('id', user_id).execute()
            if response.data:
                logger.info(f"用户头像URL更新成功: {user_id}")
                return {"success": True, "data": {"avatar_url": avatar_url}}
            else:
                raise ValueError("头像URL更新失败")
        except Exception as e:
            logger.error(f"更新头像URL失败: {e}")
            raise ValueError(f"更新头像URL失败: {e}")
