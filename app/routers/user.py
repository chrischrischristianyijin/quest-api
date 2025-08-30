from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.models.user import UserUpdate
from typing import Dict, Any
import logging
import uuid
import os
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(tags=["用户管理"])
security = HTTPBearer()

@router.post("/upload-avatar", response_model=Dict[str, Any])
async def upload_avatar(
    avatar: UploadFile = File(...),
    user_id: str = Form(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """上传用户头像"""
    try:
        # 验证令牌
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        if current_user["id"] != user_id:
            raise HTTPException(status_code=403, detail="无权限上传其他用户的头像")
        
        # 验证文件类型
        if not avatar.content_type or not avatar.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="只支持图片文件")
        
        # 验证文件大小 (5MB)
        file_content = await avatar.read()
        if len(file_content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过5MB")
        
        # 生成唯一文件名
        file_extension = Path(avatar.filename).suffix.lower()
        if not file_extension:
            file_extension = '.jpg'  # 默认扩展名
        
        unique_filename = f"{user_id}_{uuid.uuid4()}{file_extension}"
        
        # 上传到Supabase Storage
        user_service = UserService()
        avatar_url = await user_service.upload_avatar_file(file_content, unique_filename, avatar.content_type)
        
        # 更新用户资料中的头像URL
        result = await user_service.upload_avatar(user_id, avatar_url)
        
        logger.info(f"头像上传成功: {user_id} -> {avatar_url}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传头像失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传头像失败: {str(e)}")

@router.put("/profile", response_model=Dict[str, Any])
async def update_profile(
    user_update: UserUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """更新用户资料"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        user_service = UserService()
        result = await user_service.update_user_profile(current_user["id"], user_update)
        
        return result
    except Exception as e:
        logger.error(f"更新用户资料失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile", response_model=Dict[str, Any])
async def get_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取用户资料"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        user_service = UserService()
        result = await user_service.get_user_profile(current_user["id"])
        
        return result
    except Exception as e:
        logger.error(f"获取用户资料失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
