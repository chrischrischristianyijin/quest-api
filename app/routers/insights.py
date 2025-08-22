from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.insights_service import InsightsService
from app.services.auth_service import AuthService
from app.models.insight import InsightCreate, InsightUpdate, InsightResponse, InsightListResponse
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["见解管理"])
security = HTTPBearer()

@router.get("/", response_model=InsightListResponse)
async def get_insights(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取见解列表（分页）"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        insights_service = InsightsService()
        result = await insights_service.get_insights(
            page=page,
            limit=limit,
            user_id=user_id or current_user["id"],
            search=search
        )
        
        return result
    except Exception as e:
        logger.error(f"获取见解列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all", response_model=InsightListResponse)
async def get_all_user_insights(
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取用户所有见解（不分页）"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        insights_service = InsightsService()
        result = await insights_service.get_all_user_insights(
            user_id=user_id or current_user["id"],
            search=search
        )
        
        return result
    except Exception as e:
        logger.error(f"获取用户所有见解失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{insight_id}", response_model=InsightResponse)
async def get_insight(
    insight_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取见解详情"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        insights_service = InsightsService()
        result = await insights_service.get_insight(insight_id)
        
        # 安全检查：确保用户只能访问自己的insights
        if result.data["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=403, 
                detail="无权限访问此insight"
            )
        
        return result
    except Exception as e:
        logger.error(f"获取见解详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=InsightResponse)
async def create_insight(
    insight: InsightCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """创建新见解"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        insights_service = InsightsService()
        result = await insights_service.create_insight(insight, current_user["id"])
        
        return result
    except Exception as e:
        logger.error(f"创建见解失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{insight_id}", response_model=InsightResponse)
async def update_insight(
    insight_id: str,
    insight: InsightUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """更新见解"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        insights_service = InsightsService()
        result = await insights_service.update_insight(insight_id, insight, current_user["id"])
        
        return result
    except Exception as e:
        logger.error(f"更新见解失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{insight_id}")
async def delete_insight(
    insight_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """删除见解"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        insights_service = InsightsService()
        result = await insights_service.delete_insight(insight_id, current_user["id"])
        
        return result
    except Exception as e:
        logger.error(f"删除见解失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
