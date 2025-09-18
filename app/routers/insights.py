from fastapi import APIRouter, HTTPException, Depends, status, Query, Response
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
    stack_id: Optional[int] = Query(None, description="堆叠ID筛选"),
    include_tags: bool = Query(False, description="是否包含标签信息"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取见解列表（分页）"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        logger.info(f"用户 {current_user['id']} 请求insights列表，page={page}, limit={limit}, search={search}, user_id={user_id}, stack_id={stack_id}")
        
        insights_service = InsightsService()
        result = await insights_service.get_insights(
            user_id=UUID(current_user["id"]),
            page=page,
            limit=limit,
            search=search,
            target_user_id=user_id,
            stack_id=stack_id,
            include_tags=include_tags
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

@router.get("/sync/incremental")
async def get_insights_incremental(
    response: Response,
    since: Optional[str] = Query(None, description="上次同步时间戳 (ISO 格式)"),
    etag: Optional[str] = Query(None, description="上次响应的 ETag"),
    limit: int = Query(50, ge=1, le=100, description="每次获取数量"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """增量获取见解（只返回变动的数据）"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        logger.info(f"用户 {current_user['id']} 请求增量insights，since={since}, etag={etag}")
        
        insights_service = InsightsService()
        result = await insights_service.get_insights_incremental(
            user_id=UUID(current_user["id"]),
            since=since,
            etag=etag,
            limit=limit
        )
        
        if not result.get("success"):
            # 特殊处理 304 Not Modified
            if result.get("not_modified"):
                response.status_code = 304
                if result.get("etag"):
                    response.headers["ETag"] = result["etag"]
                return {"not_modified": True}
            
            logger.warning(f"增量获取insights失败: {result.get('message')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "增量获取insights失败")
            )
        
        # 设置缓存头
        if result.get("data", {}).get("etag"):
            response.headers["ETag"] = result["data"]["etag"]
            response.headers["Cache-Control"] = "private, must-revalidate"
        
        logger.info(f"用户 {current_user['id']} 成功获取增量insights")
        return result
    except Exception as e:
        logger.error(f"增量获取见解失败: {e}")
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

@router.get("/{insight_id}/status")
async def get_insight_status(
    insight_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取insight的处理状态和最新数据"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        insights_service = InsightsService()
        result = await insights_service.get_insight_status(insight_id, UUID(current_user["id"]))
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "获取insight状态失败")
            )
        
        return result
    except Exception as e:
        logger.error(f"获取insight状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_insight(
    insight: InsightCreateFromURL,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """创建新见解（轻写入模式：立即返回，异步处理metadata）"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        # 🚀 轻写入模式：立即创建基础insight记录，不等待metadata抓取
        insights_service = InsightsService()
        result = await insights_service.create_insight_light(
            url=insight.url,
            title=insight.title,  # 用户自定义标题（如果有）
            thought=insight.thought,
            tag_ids=insight.tag_ids,
            stack_id=insight.stack_id,
            user_id=UUID(current_user["id"])
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "创建insight失败")
            )
        
        # 🎯 启动异步metadata抓取任务（不等待完成）
        insight_id = result["data"]["id"]
        try:
            import asyncio
            asyncio.create_task(insights_service._fetch_metadata_async(
                insight_id=insight_id,
                url=insight.url,
                user_id=UUID(current_user["id"])
            ))
            logger.info(f"已启动异步metadata抓取任务: insight_id={insight_id}")
        except Exception as task_err:
            logger.warning(f"启动异步metadata抓取任务失败: {task_err}")
        
        return result
    except Exception as e:
        logger.error(f"创建见解失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/stack-ids")
async def debug_stack_ids(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """调试端点：检查数据库中的stack_id状态"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        from app.core.database import get_supabase_service
        supabase_service = get_supabase_service()
        
        # 查询最近的insights
        response = supabase_service.table('insights').select('id, title, stack_id, created_at').order('created_at', desc=True).limit(10).execute()
        
        insights = response.data or []
        logger.info(f"🔍 DEBUG: 最近10个insights的stack_id状态:")
        
        for insight in insights:
            logger.info(f"🔍 DEBUG: Insight {insight['id']}: title='{insight['title']}', stack_id={insight['stack_id']}, type={type(insight['stack_id'])}")
        
        # 查询所有stacks
        stacks_response = supabase_service.table('stacks').select('id, name').execute()
        stacks = stacks_response.data or []
        logger.info(f"🔍 DEBUG: 所有stacks:")
        
        for stack in stacks:
            logger.info(f"🔍 DEBUG: Stack {stack['id']}: name='{stack['name']}'")
        
        return {
            "success": True,
            "message": "Debug information logged",
            "data": {
                "insights": insights,
                "stacks": stacks
            }
        }
        
    except Exception as e:
        logger.error(f"调试查询失败: {e}")
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

