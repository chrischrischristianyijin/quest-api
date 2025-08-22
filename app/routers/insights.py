from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.insights_service import InsightsService
from app.services.auth_service import AuthService
from app.models.insight import InsightCreate, InsightCreateFromURL, InsightUpdate, InsightResponse, InsightListResponse
from typing import Dict, Any, List, Optional
from uuid import UUID
import logging
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

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
        
        # 从URL提取metadata
        metadata = await extract_metadata_from_url(insight.url)
        
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
            
            return {
                "title": title,
                "description": description,
                "image_url": image_url,
                "domain": urlparse(url).netloc,
                "extracted_at": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"提取metadata失败: {e}")
        return {
            "title": "无标题",
            "description": "",
            "image_url": None,
            "domain": urlparse(url).netloc if url else None,
            "extracted_at": datetime.utcnow().isoformat()
        }

def extract_title(soup: BeautifulSoup) -> str:
    """提取网页标题"""
    # 优先提取og:title
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        return og_title['content'].strip()
    
    # 其次提取title标签
    title_tag = soup.find('title')
    if title_tag and title_tag.text:
        return title_tag.text.strip()
    
    # 最后提取h1标签
    h1_tag = soup.find('h1')
    if h1_tag and h1_tag.text:
        return h1_tag.text.strip()
    
    return "无标题"

def extract_description(soup: BeautifulSoup) -> str:
    """提取网页描述"""
    # 优先提取og:description
    og_desc = soup.find('meta', property='og:description')
    if og_desc and og_desc.get('content'):
        return og_desc['content'].strip()
    
    # 其次提取description meta标签
    desc_tag = soup.find('meta', attrs={'name': 'description'})
    if desc_tag and desc_tag.get('content'):
        return desc_tag['content'].strip()
    
    # 最后提取第一个p标签
    p_tag = soup.find('p')
    if p_tag and p_tag.text:
        text = p_tag.text.strip()
        return text[:300] + "..." if len(text) > 300 else text
    
    return ""

def extract_image(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """提取网页图片"""
    # 优先提取og:image
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        image_url = og_image['content']
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif image_url.startswith('/'):
            parsed = urlparse(base_url)
            image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"
        return image_url
    
    # 其次提取第一个img标签
    img_tag = soup.find('img')
    if img_tag and img_tag.get('src'):
        image_url = img_tag['src']
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif image_url.startswith('/'):
            parsed = urlparse(base_url)
            image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"
        return image_url
    
    return None
