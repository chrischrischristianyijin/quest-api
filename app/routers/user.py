from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.user import UserUpdate, UserProfile, FollowRequest, FollowStatus
from app.services.user_service import UserService
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

@router.get("/profile/{email}", response_model=Dict[str, Any])
async def get_user_profile(email: str):
    """获取用户资料"""
    try:
        user_service = UserService()
        profile = await user_service.get_user_profile(email)
        return {
            "success": True,
            "data": profile
        }
    except Exception as e:
        logger.error(f"获取用户资料失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

@router.put("/profile/{email}", response_model=Dict[str, Any])
async def update_user_profile(
    email: str, 
    profile: UserUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """更新用户资料"""
    try:
        user_service = UserService()
        result = await user_service.update_user_profile(email, profile, credentials.credentials)
        return {
            "success": True,
            "message": "更新成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"更新用户资料失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/upload-avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """上传头像"""
    try:
        user_service = UserService()
        result = await user_service.upload_avatar(avatar, credentials.credentials)
        return {
            "success": True,
            "message": "头像上传成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"头像上传失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/followers/{email}", response_model=Dict[str, Any])
async def get_followers(email: str):
    """获取粉丝列表"""
    try:
        user_service = UserService()
        followers = await user_service.get_followers(email)
        return {
            "success": True,
            "data": followers
        }
    except Exception as e:
        logger.error(f"获取粉丝列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/following/{email}", response_model=Dict[str, Any])
async def get_following(email: str):
    """获取关注列表"""
    try:
        user_service = UserService()
        following = await user_service.get_following(email)
        return {
            "success": True,
            "data": following
        }
    except Exception as e:
        logger.error(f"获取关注列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/follow", response_model=Dict[str, Any])
async def follow_user(
    follow_request: FollowRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """关注用户"""
    try:
        user_service = UserService()
        result = await user_service.follow_user(follow_request, credentials.credentials)
        return {
            "success": True,
            "message": "关注成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"关注用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/follow", response_model=Dict[str, Any])
async def unfollow_user(
    follow_request: FollowRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """取消关注"""
    try:
        user_service = UserService()
        result = await user_service.unfollow_user(follow_request, credentials.credentials)
        return {
            "success": True,
            "message": "取消关注成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"取消关注失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/follow-status", response_model=Dict[str, Any])
async def get_follow_status(
    target_email: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取关注状态"""
    try:
        user_service = UserService()
        status = await user_service.get_follow_status(target_email, credentials.credentials)
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"获取关注状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
