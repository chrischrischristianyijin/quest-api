
from fastapi import APIRouter, HTTPException, Depends, status, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.auth_service import AuthService
from app.core.database import get_supabase
from typing import Dict, Any, Optional
import logging
from app.utils.metadata import (
    extract_metadata_from_url as utils_extract_metadata_from_url,
    is_valid_url as utils_is_valid_url,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["元数据"])
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户"""
    auth_service = AuthService()
    return await auth_service.get_current_user(credentials.credentials)

@router.get("/", response_model=Dict[str, Any])
async def get_metadata():
    """获取系统元数据"""
    return {
        "success": True,
        "message": "获取元数据成功",
        "data": {
            "system_info": "Quest API v1.0.0",
            "categories": ["技术", "生活", "学习", "其他"],
            "tags": ["Python", "FastAPI", "Supabase", "Web开发"]
        }
    }



@router.post("/extract", response_model=Dict[str, Any])
async def extract_webpage_metadata(
    url: str = Form(..., description="要提取元数据的网页URL")
):
    """提取网页元数据 - 仅提取，不创建insight"""
    try:
        # 验证URL格式
        if not utils_is_valid_url(url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的URL格式"
            )
        
        # 提取元数据
        metadata = await utils_extract_metadata_from_url(url)
        
        # 返回提取的metadata信息
        return {
            "success": True,
            "message": "元数据提取成功",
            "data": {
                "url": url,
                "title": metadata.get("title", "无标题"),
                "description": metadata.get("description", ""),
                "image_url": metadata.get("image_url"),
                "suggested_tags": [],  # 可以基于内容智能推荐标签
                "domain": metadata.get("domain"),
                "extracted_at": metadata.get("extracted_at")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取元数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="元数据提取失败"
        )

@router.post("/create-insight", response_model=Dict[str, Any])
async def create_insight_from_url(
    url: str = Form(..., description="网页URL"),
    title: Optional[str] = Form(None, description="自定义标题（已废弃，忽略）"),
    description: Optional[str] = Form(None, description="自定义描述（已废弃，忽略）"),
    tags: Optional[str] = Form(None, description="标签（已废弃，忽略）"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """已废弃：仅提取并返回元数据，不创建insight。请改用 POST /api/v1/insights 创建。"""
    try:
        # 验证URL格式
        if not utils_is_valid_url(url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的URL格式"
            )

        # 仅提取元数据并返回（与 /extract 对齐）
        metadata = await utils_extract_metadata_from_url(url)
        return {
            "success": True,
            "message": "此端点已废弃，仅返回元数据。请改用 /api/v1/insights 创建。",
            "data": {
                "url": url,
                "title": metadata.get("title", "无标题"),
                "description": metadata.get("description", ""),
                "image_url": metadata.get("image_url"),
                "suggested_tags": [],
                "domain": metadata.get("domain"),
                "extracted_at": metadata.get("extracted_at")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从URL提取元数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="元数据提取失败"
        )




@router.get("/preview/{insight_id}", response_model=Dict[str, Any])
async def preview_insight(
    insight_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """预览insight内容"""
    try:
        supabase = get_supabase()
        
        # 获取insight信息
        response = supabase.table('insights').select('*').eq('id', insight_id).eq('user_id', current_user["id"]).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="insight不存在或无权限访问"
            )
        
        insight = response.data
        
        # 如果insight有URL，尝试获取最新元数据
        if insight.get('url'):
            try:
                latest_metadata = await utils_extract_metadata_from_url(insight['url'])
                insight['latest_metadata'] = latest_metadata
            except:
                insight['latest_metadata'] = None
        
        return {
            "success": True,
            "message": "获取insight预览成功",
            "data": insight
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取insight预览失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取预览失败"
        )
