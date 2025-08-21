from app.core.database import get_supabase_client
from app.models.insight import InsightCreate, InsightUpdate, InsightResponse, InsightListResponse
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class InsightsService:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def get_insights(
        self,
        page: int = 1,
        limit: int = 10,
        user_id: Optional[str] = None,
        search: Optional[str] = None
    ) -> InsightListResponse:
        """获取见解列表"""
        try:
            # 构建查询
            query = self.supabase.table("insights").select("*")
            
            # 用户筛选
            if user_id:
                query = query.eq("user_id", user_id)
            
            # 搜索功能
            if search:
                query = query.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")
            
            # 分页
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1)
            
            # 按创建时间倒序
            query = query.order("created_at", desc=True)
            
            # 执行查询
            response = query.execute()
            
            if response.error:
                logger.error(f"查询insights失败: {response.error}")
                raise Exception(f"数据库查询失败: {response.error}")
            
            insights = response.data or []
            
            # 获取总数
            count_query = self.supabase.table("insights").select("id", count="exact")
            if user_id:
                count_query = count_query.eq("user_id", user_id)
            if search:
                count_query = count_query.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")
            
            count_response = count_query.execute()
            total = count_response.count if count_response.count is not None else 0
            
            # 构建响应
            insight_responses = []
            for insight in insights:
                insight_responses.append(InsightResponse(
                    id=insight["id"],
                    user_id=insight["user_id"],
                    url=insight.get("url"),
                    title=insight["title"],
                    description=insight["description"],
                    image_url=insight.get("image_url"),
                    tags=insight.get("tags", []),
                    created_at=insight["created_at"],
                    updated_at=insight.get("updated_at")
                ))
            
            return InsightListResponse(
                success=True,
                data={
                    "insights": insight_responses,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total,
                        "total_pages": (total + limit - 1) // limit
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"获取insights失败: {e}")
            raise Exception(f"获取insights失败: {str(e)}")
    
    async def get_insight(self, insight_id: str) -> InsightResponse:
        """获取见解详情"""
        try:
            response = self.supabase.table("insights").select("*").eq("id", insight_id).execute()
            
            if response.error:
                logger.error(f"查询insight失败: {response.error}")
                raise Exception(f"数据库查询失败: {response.error}")
            
            if not response.data:
                raise Exception("Insight不存在")
            
            insight = response.data[0]
            
            return InsightResponse(
                id=insight["id"],
                user_id=insight["user_id"],
                url=insight.get("url"),
                title=insight["title"],
                description=insight["description"],
                image_url=insight.get("image_url"),
                tags=insight.get("tags", []),
                created_at=insight["created_at"],
                updated_at=insight.get("updated_at")
            )
            
        except Exception as e:
            logger.error(f"获取insight失败: {e}")
            raise Exception(f"获取insight失败: {str(e)}")
    
    async def create_insight(self, insight: InsightCreate, user_id: str) -> InsightResponse:
        """创建新见解"""
        try:
            # 生成UUID
            insight_id = str(uuid.uuid4())
            current_time = datetime.utcnow().isoformat()
            
            # 准备数据
            insight_data = {
                "id": insight_id,
                "user_id": user_id,
                "url": insight.url,
                "title": insight.title,
                "description": insight.description,
                "image_url": insight.image_url,
                "tags": insight.tags or [],
                "created_at": current_time,
                "updated_at": current_time
            }
            
            # 插入数据库
            response = self.supabase.table("insights").insert(insight_data).execute()
            
            if response.error:
                logger.error(f"创建insight失败: {response.error}")
                raise Exception(f"数据库插入失败: {response.error}")
            
            logger.info(f"成功创建insight: {insight_id}")
            
            # 返回创建的insight
            return InsightResponse(
                id=insight_id,
                user_id=user_id,
                url=insight.url,
                title=insight.title,
                description=insight.description,
                image_url=insight.image_url,
                tags=insight.tags or [],
                created_at=current_time,
                updated_at=current_time
            )
            
        except Exception as e:
            logger.error(f"创建insight失败: {e}")
            raise Exception(f"创建insight失败: {str(e)}")
    
    async def update_insight(
        self,
        insight_id: str,
        insight: InsightUpdate,
        user_id: str
    ) -> InsightResponse:
        """更新见解"""
        try:
            # 检查insight是否存在且属于当前用户
            existing_response = self.supabase.table("insights").select("*").eq("id", insight_id).eq("user_id", user_id).execute()
            
            if existing_response.error:
                logger.error(f"查询insight失败: {existing_response.error}")
                raise Exception(f"数据库查询失败: {existing_response.error}")
            
            if not existing_response.data:
                raise Exception("Insight不存在或无权限修改")
            
            existing_insight = existing_response.data[0]
            current_time = datetime.utcnow().isoformat()
            
            # 准备更新数据
            update_data = {
                "updated_at": current_time
            }
            
            if insight.title is not None:
                update_data["title"] = insight.title
            if insight.description is not None:
                update_data["description"] = insight.description
            if insight.url is not None:
                update_data["url"] = insight.url
            if insight.image_url is not None:
                update_data["image_url"] = insight.image_url
            if insight.tags is not None:
                update_data["tags"] = insight.tags
            
            # 更新数据库
            response = self.supabase.table("insights").update(update_data).eq("id", insight_id).execute()
            
            if response.error:
                logger.error(f"更新insight失败: {response.error}")
                raise Exception(f"数据库更新失败: {response.error}")
            
            logger.info(f"成功更新insight: {insight_id}")
            
            # 返回更新后的insight
            return InsightResponse(
                id=insight_id,
                user_id=user_id,
                url=update_data.get("url", existing_insight.get("url")),
                title=update_data.get("title", existing_insight["title"]),
                description=update_data.get("description", existing_insight["description"]),
                image_url=update_data.get("image_url", existing_insight.get("image_url")),
                tags=update_data.get("tags", existing_insight.get("tags", [])),
                created_at=existing_insight["created_at"],
                updated_at=current_time
            )
            
        except Exception as e:
            logger.error(f"更新insight失败: {e}")
            raise Exception(f"更新insight失败: {str(e)}")
    
    async def delete_insight(self, insight_id: str, user_id: str) -> Dict[str, Any]:
        """删除见解"""
        try:
            # 检查insight是否存在且属于当前用户
            existing_response = self.supabase.table("insights").select("id").eq("id", insight_id).eq("user_id", user_id).execute()
            
            if existing_response.error:
                logger.error(f"查询insight失败: {existing_response.error}")
                raise Exception(f"数据库查询失败: {existing_response.error}")
            
            if not existing_response.data:
                raise Exception("Insight不存在或无权限删除")
            
            # 删除insight
            response = self.supabase.table("insights").delete().eq("id", insight_id).execute()
            
            if response.error:
                logger.error(f"删除insight失败: {response.error}")
                raise Exception(f"数据库删除失败: {response.error}")
            
            logger.info(f"成功删除insight: {insight_id}")
            
            return {
                "success": True,
                "message": "见解删除成功"
            }
            
        except Exception as e:
            logger.error(f"删除insight失败: {e}")
            raise Exception(f"删除insight失败: {str(e)}")
