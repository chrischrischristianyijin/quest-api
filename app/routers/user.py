from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.models.user import UserUpdate
from typing import Dict, Any
import logging

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
        
        # 这里应该实现文件上传到存储服务的逻辑
        # 暂时返回模拟的URL
        avatar_url = f"https://example.com/avatars/{user_id}.jpg"
        
        user_service = UserService()
        result = await user_service.upload_avatar(user_id, avatar_url)
        
        return result
    except Exception as e:
        logger.error(f"上传头像失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
