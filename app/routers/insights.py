from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.insights_service import InsightsService
from app.services.auth_service import AuthService
from app.models.insight import InsightCreate, InsightCreateFromURL, InsightUpdate, InsightResponse, InsightListResponse
from typing import Dict, Any, List, Optional
from uuid import UUID
import logging
from app.utils.metadata import (
    extract_metadata_from_url as utils_extract_metadata_from_url,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["见解管理"])
security = HTTPBearer()

@router.get("/")
async def get_insights(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    user_id: Optional[UUID] = Query(None, description="用户ID筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取见解列表（分页）"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        logger.info(f"用户 {current_user['id']} 请求insights列表，page={page}, limit={limit}, search={search}, user_id={user_id}")
        
        insights_service = InsightsService()
        result = await insights_service.get_insights(
            user_id=UUID(current_user["id"]),
            page=page,
            limit=limit,
            search=search,
            target_user_id=user_id
        )
        
        if not result.get("success"):
            logger.warning(f"获取insights失败: {result.get('message')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "获取insights失败")
            )
        
        logger.info(f"用户 {current_user['id']} 成功获取insights列表")
        return result
    except Exception as e:
        logger.error(f"获取见解列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all")
async def get_all_user_insights(
    user_id: Optional[UUID] = Query(None, description="用户ID筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取用户所有见解（不分页）"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        logger.info(f"用户 {current_user['id']} 请求所有insights，search={search}, user_id={user_id}")
        
        insights_service = InsightsService()
        result = await insights_service.get_all_user_insights(
            user_id=UUID(current_user["id"]),
            search=search,
            target_user_id=user_id
        )
        
        if not result.get("success"):
            logger.warning(f"获取所有insights失败: {result.get('message')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "获取所有insights失败")
            )
        
        logger.info(f"用户 {current_user['id']} 成功获取所有insights")
        return result
    except Exception as e:
        logger.error(f"获取用户所有见解失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{insight_id}")
async def get_insight(
    insight_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取见解详情"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        insights_service = InsightsService()
        result = await insights_service.get_insight(insight_id, UUID(current_user["id"]))
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "获取insight失败")
            )
        
        return result
    except Exception as e:
        logger.error(f"获取见解详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_insight(
    insight: InsightCreateFromURL,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """创建新见解（从URL自动获取metadata）"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        # 从URL提取metadata（统一使用utils）
        metadata = await utils_extract_metadata_from_url(insight.url)
        
        # 创建完整的insight数据
        insight_data = InsightCreate(
            title=metadata.get("title", "无标题"),
            description=metadata.get("description", ""),
            url=insight.url,
            image_url=metadata.get("image_url"),
            thought=insight.thought,
            tag_ids=insight.tag_ids
        )
        
        insights_service = InsightsService()
        result = await insights_service.create_insight(insight_data, UUID(current_user["id"]))
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "创建insight失败")
            )
        
        return result
    except Exception as e:
        logger.error(f"创建见解失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{insight_id}")
async def update_insight(
    insight_id: UUID,
    insight: InsightUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """更新见解"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        insights_service = InsightsService()
        result = await insights_service.update_insight(insight_id, insight, UUID(current_user["id"]))
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "更新insight失败")
            )
        
        return result
    except Exception as e:
        logger.error(f"更新见解失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{insight_id}")
async def delete_insight(
    insight_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """删除见解"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        insights_service = InsightsService()
        result = await insights_service.delete_insight(insight_id, UUID(current_user["id"]))
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "删除insight失败")
            )
        
        return result
    except Exception as e:
        logger.error(f"删除见解失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

        return result
