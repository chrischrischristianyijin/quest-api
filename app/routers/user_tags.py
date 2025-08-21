from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.insight import UserTagCreate, UserTagUpdate, UserTagResponse
from app.services.auth_service import AuthService
from app.services.user_tag_service import UserTagService
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/user-tags", tags=["用户标签管理"])
security = HTTPBearer()

@router.get("/", response_model=Dict[str, Any])
async def get_user_tags(
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取用户标签列表"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        user_tag_service = UserTagService()
        result = await user_tag_service.get_user_tags(
            user_id=user_id or current_user["id"],
            page=page,
            limit=limit
        )
        
        return result
    except Exception as e:
        logger.error(f"获取用户标签失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{tag_id}", response_model=Dict[str, Any])
async def get_tag_by_id(
    tag_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """根据ID获取标签详情"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        user_tag_service = UserTagService()
        result = await user_tag_service.get_tag_by_id(tag_id)
        
        return result
    except Exception as e:
        logger.error(f"获取标签详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict[str, Any])
async def create_tag(
    tag: UserTagCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """创建新标签"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        user_tag_service = UserTagService()
        result = await user_tag_service.create_tag(tag.dict(), current_user["id"])
        
        return result
    except Exception as e:
        logger.error(f"创建标签失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{tag_id}", response_model=Dict[str, Any])
async def update_tag(
    tag_id: str,
    tag: UserTagUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """更新标签"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        user_tag_service = UserTagService()
        result = await user_tag_service.update_tag(tag_id, tag.dict(exclude_unset=True), current_user["id"])
        
        return result
    except Exception as e:
        logger.error(f"更新标签失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """删除标签"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        user_tag_service = UserTagService()
        result = await user_tag_service.delete_tag(tag_id, current_user["id"])
        
        return result
    except Exception as e:
        logger.error(f"删除标签失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_tag_stats(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取标签统计信息"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        user_tag_service = UserTagService()
        result = await user_tag_service.get_tag_stats(current_user["id"])
        
        return result
    except Exception as e:
        logger.error(f"获取标签统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=Dict[str, Any])
async def search_tags(
    q: str = Query(..., description="搜索关键词"),
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """搜索标签"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        user_tag_service = UserTagService()
        result = await user_tag_service.search_tags(q, user_id or current_user["id"])
        
        return result
    except Exception as e:
        logger.error(f"搜索标签失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
