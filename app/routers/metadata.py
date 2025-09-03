
from fastapi import APIRouter, HTTPException, Depends, status, Form, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.auth_service import AuthService
from app.core.database import get_supabase, get_supabase_service
from typing import Dict, Any, Optional
import logging
import asyncio
from app.utils.metadata import (
    extract_metadata_from_url as utils_extract_metadata_from_url,
    is_valid_url as utils_is_valid_url,
    fetch_page_content,
)
from app.utils.summarize import generate_summary
import time
from datetime import datetime, timedelta

# 简单的内存缓存来存储摘要结果
summary_cache = {}

logger = logging.getLogger(__name__)
router = APIRouter(tags=["元数据"])
security = HTTPBearer()

async def generate_summary_background(url: str, metadata: Dict[str, Any]):
    """后台异步生成摘要并缓存"""
    try:
        logger.info(f"开始为 URL {url} 生成摘要")
        
        # 初始化缓存状态
        summary_cache[url] = {
            'status': 'generating',
            'created_at': datetime.now(),
            'summary': None,
            'error': None
        }
        
        # 获取页面内容
        page_content = await fetch_page_content(url)
        text_content = page_content.get('text', '')
        
        if not text_content:
            # 如果没有文本内容，使用元数据中的描述
            text_content = metadata.get('description', '')
        
        if text_content:
            # 生成摘要
            summary = await generate_summary(text_content)
            if summary:
                # 更新缓存
                summary_cache[url] = {
                    'status': 'completed',
                    'created_at': datetime.now(),
                    'summary': summary,
                    'error': None
                }
                
                logger.info(f"URL {url} 摘要生成成功: {summary[:100]}...")
            else:
                # 更新失败状态
                summary_cache[url] = {
                    'status': 'failed',
                    'created_at': datetime.now(),
                    'summary': None,
                    'error': '摘要生成失败'
                }
                logger.warning(f"URL {url} 摘要生成失败")
        else:
            # 更新失败状态
            summary_cache[url] = {
                'status': 'failed',
                'created_at': datetime.now(),
                'summary': None,
                'error': '没有可用的文本内容'
            }
            logger.warning(f"URL {url} 没有可用的文本内容用于生成摘要")
            
    except Exception as e:
        summary_cache[url] = {
            'status': 'failed',
            'created_at': datetime.now(),
            'summary': None,
            'error': str(e)
        }
        logger.error(f"为 URL {url} 生成摘要时出错: {e}")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户"""
    auth_service = AuthService()
    return await auth_service.get_current_user(credentials.credentials)



@router.post("/extract", response_model=Dict[str, Any])
async def extract_webpage_metadata(
    url: str = Form(..., description="要提取元数据的网页URL"),
    background_tasks: BackgroundTasks = None
):
    """提取网页元数据 - 后台异步生成摘要并缓存"""
    try:
        # 验证URL格式
        if not utils_is_valid_url(url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的URL格式"
            )
        
        # 提取元数据
        metadata = await utils_extract_metadata_from_url(url)
        
        # 添加后台任务：异步生成摘要
        if background_tasks:
            background_tasks.add_task(generate_summary_background, url, metadata)
            logger.info(f"已添加后台摘要生成任务: {url}")
        
        # 返回提取的metadata信息
        return {
            "success": True,
            "message": "元数据提取成功，摘要生成任务已启动",
            "data": {
                "url": url,
                "title": metadata.get("title", "无标题"),
                "description": metadata.get("description", ""),
                "image_url": metadata.get("image_url"),
                "suggested_tags": [],  # 可以基于内容智能推荐标签
                "domain": metadata.get("domain"),
                "extracted_at": metadata.get("extracted_at"),
                "summary_status": "generating" if background_tasks else "disabled"
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

@router.get("/summary/{url:path}", response_model=Dict[str, Any])
async def get_summary_status(url: str):
    """获取URL的摘要生成状态和结果"""
    try:
        # 清理过期的缓存（超过1小时）
        current_time = datetime.now()
        expired_urls = []
        for cached_url, cache_data in summary_cache.items():
            if current_time - cache_data['created_at'] > timedelta(hours=1):
                expired_urls.append(cached_url)
        
        for expired_url in expired_urls:
            del summary_cache[expired_url]
        
        # 检查是否有缓存
        if url not in summary_cache:
            return {
                "success": True,
                "message": "摘要未生成或已过期",
                "data": {
                    "url": url,
                    "status": "not_found",
                    "summary": None,
                    "error": None,
                    "created_at": None
                }
            }
        
        cache_data = summary_cache[url]
        return {
            "success": True,
            "message": f"摘要状态: {cache_data['status']}",
            "data": {
                "url": url,
                "status": cache_data['status'],
                "summary": cache_data['summary'],
                "error": cache_data['error'],
                "created_at": cache_data['created_at'].isoformat() if cache_data['created_at'] else None
            }
        }
    except Exception as e:
        logger.error(f"获取摘要状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取摘要状态失败"
        )
