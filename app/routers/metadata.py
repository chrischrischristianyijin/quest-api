
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

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
