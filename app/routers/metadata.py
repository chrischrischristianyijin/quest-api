
from fastapi import APIRouter, HTTPException, Depends, status, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.insight import InsightCreate
from app.services.auth_service import AuthService
from app.core.database import get_supabase
from typing import Dict, Any, Optional
import logging
import httpx
import re
from bs4 import BeautifulSoup
import uuid
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
router = APIRouter()
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
    """提取网页元数据"""
    try:
        # 验证URL格式
        if not is_valid_url(url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的URL格式"
            )
        
        # 提取元数据
        metadata = await extract_metadata_from_url(url)
        
        return {
            "success": True,
            "message": "元数据提取成功",
            "data": metadata
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
    title: Optional[str] = Form(None, description="自定义标题（可选）"),
    description: Optional[str] = Form(None, description="自定义描述（可选）"),
    tags: Optional[str] = Form(None, description="标签，用逗号分隔（可选）"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """从URL创建insight"""
    try:
        # 验证URL格式
        if not is_valid_url(url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的URL格式"
            )
        
        # 提取元数据
        metadata = await extract_metadata_from_url(url)
        
        # 处理标签
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        # 创建insight数据
        insight_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "url": url,
            "title": title or metadata.get("title", "无标题"),
            "description": description or metadata.get("description", ""),
            "image_url": metadata.get("image_url"),
            "tags": tag_list,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # 保存到数据库
        supabase = get_supabase()
        response = supabase.table('insights').insert(insight_data).execute()
        
        if response.data:
            return {
                "success": True,
                "message": "从URL创建insight成功",
                "data": response.data[0]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="保存insight失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从URL创建insight失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建insight失败"
        )

@router.post("/batch-extract", response_model=Dict[str, Any])
async def batch_extract_metadata(
    urls: str = Form(..., description="多个URL，用换行符分隔")
):
    """批量提取多个URL的元数据"""
    try:
        url_list = [url.strip() for url in urls.split('\n') if url.strip()]
        
        if len(url_list) > 10:  # 限制批量处理数量
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="一次最多处理10个URL"
            )
        
        results = []
        for url in url_list:
            try:
                if is_valid_url(url):
                    metadata = await extract_metadata_from_url(url)
                    results.append({
                        "url": url,
                        "success": True,
                        "data": metadata
                    })
                else:
                    results.append({
                        "url": url,
                        "success": False,
                        "error": "无效的URL格式"
                    })
            except Exception as e:
                results.append({
                    "url": url,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": "批量元数据提取完成",
            "data": results
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量提取元数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量提取失败"
        )

def is_valid_url(url: str) -> bool:
    """验证URL格式"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

async def extract_metadata_from_url(url: str) -> Dict[str, Any]:
    """从URL提取元数据"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取标题
            title = extract_title(soup)
            
            # 提取描述
            description = extract_description(soup)
            
            # 提取图片
            image_url = extract_image(soup, url)
            
            # 提取其他元数据
            metadata = {
                "title": title,
                "description": description,
                "image_url": image_url,
                "url": url,
                "domain": urlparse(url).netloc,
                "extracted_at": datetime.utcnow().isoformat()
            }
            
            return metadata
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="请求超时"
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法访问URL: HTTP {e.response.status_code}"
        )
    except Exception as e:
        logger.error(f"提取元数据时发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="元数据提取失败"
        )

def extract_title(soup: BeautifulSoup) -> str:
    """提取页面标题"""
    # 尝试多种标题标签
    title_selectors = [
        'meta[property="og:title"]',
        'meta[name="twitter:title"]',
        'title',
        'h1',
        'h2'
    ]
    
    for selector in title_selectors:
        element = soup.select_one(selector)
        if element:
            title = element.get('content') or element.get_text(strip=True)
            if title and len(title) > 0:
                return title[:200]  # 限制标题长度
    
    return "无标题"

def extract_description(soup: BeautifulSoup) -> str:
    """提取页面描述"""
    # 尝试多种描述标签
    desc_selectors = [
        'meta[property="og:description"]',
        'meta[name="description"]',
        'meta[name="twitter:description"]',
        'meta[property="twitter:description"]'
    ]
    
    for selector in desc_selectors:
        element = soup.select_one(selector)
        if element:
            desc = element.get('content', '')
            if desc and len(desc) > 0:
                return desc[:500]  # 限制描述长度
    
    # 如果没有meta描述，尝试提取段落内容
    paragraphs = soup.find_all('p')
    if paragraphs:
        text = ' '.join([p.get_text(strip=True) for p in paragraphs[:3]])
        if text:
            return text[:500]
    
    return ""

def extract_image(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """提取页面图片"""
    # 尝试多种图片标签
    img_selectors = [
        'meta[property="og:image"]',
        'meta[name="twitter:image"]',
        'meta[property="twitter:image"]',
        'meta[property="og:image:secure_url"]'
    ]
    
    for selector in img_selectors:
        element = soup.select_one(selector)
        if element:
            img_url = element.get('content', '')
            if img_url:
                return normalize_image_url(img_url, base_url)
    
    # 如果没有meta图片，尝试提取页面中的第一张图片
    img_tag = soup.find('img')
    if img_tag:
        img_url = img_tag.get('src') or img_tag.get('data-src')
        if img_url:
            return normalize_image_url(img_url, base_url)
    
    return None

def normalize_image_url(img_url: str, base_url: str) -> str:
    """标准化图片URL"""
    if img_url.startswith('http'):
        return img_url
    elif img_url.startswith('//'):
        return 'https:' + img_url
    elif img_url.startswith('/'):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{img_url}"
    else:
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}/{img_url}"

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
                latest_metadata = await extract_metadata_from_url(insight['url'])
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
