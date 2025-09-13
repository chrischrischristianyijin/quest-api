from app.models.user import UserUpdate, UserMemoryProfile, UserMemoryConsolidationRequest
from app.core.database import get_supabase_service
from app.services.memory_profile_service import MemoryProfileService
from typing import Dict, Any, Optional
import logging
import os
from uuid import UUID
from datetime import datetime

def serialize_datetime_for_json(obj):
    """递归序列化对象中的datetime字段为ISO格式字符串"""
    if isinstance(obj, dict):
        return {k: serialize_datetime_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime_for_json(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        self.supabase_service = get_supabase_service()
        self.memory_profile_service = MemoryProfileService()

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
            if user_update.memory_profile is not None:
                memory_profile_dict = user_update.memory_profile.dict()
                # 处理datetime字段的序列化
                if memory_profile_dict.get('last_consolidated'):
                    memory_profile_dict['last_consolidated'] = memory_profile_dict['last_consolidated'].isoformat()
                update_data['memory_profile'] = memory_profile_dict

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

    async def upload_avatar_file(self, file_content: bytes, filename: str, content_type: str) -> str:
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
                file_options={"content-type": content_type}
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
                        file_options={"content-type": content_type}
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

    # 记忆档案相关方法
    
    async def consolidate_user_memories(self, user_id: str, request: Optional[UserMemoryConsolidationRequest] = None) -> Dict[str, Any]:
        """整合用户记忆到profile中"""
        try:
            user_uuid = UUID(user_id)
            memory_profile = await self.memory_profile_service.consolidate_user_memories_to_profile(user_uuid, request)
            
            # 保存到用户profile
            await self.memory_profile_service._save_memory_profile_to_user(user_uuid, memory_profile)
            
            logger.info(f"用户 {user_id} 记忆整合成功")
            return {
                "success": True,
                "message": "记忆整合成功",
                "memory_profile": serialize_datetime_for_json(memory_profile.dict())
            }
            
        except Exception as e:
            logger.error(f"整合用户记忆失败: {e}")
            return {
                "success": False,
                "message": f"整合用户记忆失败: {e}"
            }
    
    async def get_user_memory_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户记忆档案"""
        try:
            user_uuid = UUID(user_id)
            memory_profile = await self.memory_profile_service.get_user_memory_profile(user_uuid)
            
            return {
                "success": True,
                "memory_profile": serialize_datetime_for_json(memory_profile.dict())
            }
            
        except Exception as e:
            logger.error(f"获取用户记忆档案失败: {e}")
            return {
                "success": False,
                "message": f"获取用户记忆档案失败: {e}",
                "memory_profile": {}
            }
    
    async def update_memory_profile_settings(self, user_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """更新记忆档案设置"""
        try:
            user_uuid = UUID(user_id)
            success = await self.memory_profile_service.update_memory_profile_settings(user_uuid, settings)
            
            if success:
                return {
                    "success": True,
                    "message": "记忆档案设置更新成功"
                }
            else:
                return {
                    "success": False,
                    "message": "记忆档案设置更新失败"
                }
                
        except Exception as e:
            logger.error(f"更新记忆档案设置失败: {e}")
            return {
                "success": False,
                "message": f"更新记忆档案设置失败: {e}"
            }
    
    async def get_memory_summary(self, user_id: str) -> Dict[str, Any]:
        """获取用户记忆摘要"""
        try:
            user_uuid = UUID(user_id)
            summary = await self.memory_profile_service.get_memory_summary(user_uuid)
            
            return {
                "success": True,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"获取记忆摘要失败: {e}")
            return {
                "success": False,
                "message": f"获取记忆摘要失败: {e}",
                "summary": {}
            }
    
    async def auto_consolidate_memories(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """自动整合用户记忆"""
        try:
            user_uuid = UUID(user_id)
            session_uuid = UUID(session_id) if session_id else None
            
            memory_profile = await self.memory_profile_service.auto_consolidate_user_memories(user_uuid, session_uuid)
            
            if memory_profile:
                return {
                    "success": True,
                    "message": "记忆自动整合完成",
                    "memory_profile": serialize_datetime_for_json(memory_profile.dict())
                }
            else:
                return {
                    "success": True,
                    "message": "无需整合记忆"
                }
                
        except Exception as e:
            logger.error(f"自动整合记忆失败: {e}")
            return {
                "success": False,
                "message": f"自动整合记忆失败: {e}"
            }
