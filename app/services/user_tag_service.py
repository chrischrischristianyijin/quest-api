from app.core.database import get_supabase_client, get_supabase_service
from app.models.insight import UserTagCreate, UserTagUpdate, UserTagResponse
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class UserTagService:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.supabase_service = get_supabase_service()
    
    async def get_user_tags(
        self,
        user_id: Optional[str] = None,
        page: int = 1,
        limit: int = 10
    ) -> Dict[str, Any]:
        """获取用户标签列表"""
        try:
            # 使用service role客户端以确保Google登录用户也能正常访问
            query = self.supabase_service.table("user_tags").select("*")
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            # 分页
            offset = (page - 1) * limit
            query = query.range(offset, offset + limit - 1)
            
            # 按创建时间倒序
            query = query.order("created_at", desc=True)
            
            response = query.execute()
            
            # 检查响应状态
            if hasattr(response, 'error') and response.error:
                logger.error(f"查询用户标签失败: {response.error}")
                raise Exception(f"数据库查询失败: {response.error}")
            
            tags = response.data or []
            
            # 获取总数
            count_query = self.supabase_service.table("user_tags").select("id", count="exact")
            if user_id:
                count_query = count_query.eq("user_id", user_id)
            
            count_response = count_query.execute()
            total = count_response.count if hasattr(count_response, 'count') and count_response.count is not None else 0
            
            return {
                "success": True,
                "data": tags,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": (total + limit - 1) // limit
                }
            }
            
        except Exception as e:
            logger.error(f"获取用户标签失败: {e}")
            raise Exception(f"获取用户标签失败: {str(e)}")
    
    async def get_tag_by_id(self, tag_id: str) -> Dict[str, Any]:
        """根据ID获取标签详情"""
        try:
            response = self.supabase.table("user_tags").select("*").eq("id", tag_id).execute()
            
            # 检查响应状态
            if hasattr(response, 'error') and response.error:
                logger.error(f"查询标签失败: {response.error}")
                raise Exception(f"数据库查询失败: {response.error}")
            
            if not response.data:
                raise Exception("标签不存在")
            
            return {
                "success": True,
                "data": response.data[0]
            }
            
        except Exception as e:
            logger.error(f"获取标签详情失败: {e}")
            raise Exception(f"获取标签详情失败: {str(e)}")
    
    async def create_tag(self, tag_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """创建新标签"""
        try:
            # 让数据库自动生成UUID，而不是手动生成
            current_time = datetime.utcnow().isoformat()
            
            # 准备数据
            tag_data_to_insert = {
                # 移除手动UUID生成，让数据库自动生成
                "user_id": user_id,
                "name": tag_data["name"],
                "color": tag_data["color"],
                "created_at": current_time,
                "updated_at": current_time
            }
            
            # 插入数据库（使用service role避免RLS问题）
            response = self.supabase_service.table("user_tags").insert(tag_data_to_insert).execute()
            
            # 检查响应状态
            if hasattr(response, 'error') and response.error:
                logger.error(f"创建标签失败: {response.error}")
                raise Exception(f"数据库插入失败: {response.error}")
            
            # 从响应中获取自动生成的UUID
            created_tag = response.data[0] if response.data else None
            if not created_tag:
                raise Exception("标签创建失败，未返回数据")
            
            tag_id = created_tag.get('id')
            logger.info(f"成功创建标签: {tag_id}")
            
            return {
                "success": True,
                "message": "标签创建成功",
                "data": {
                    "id": tag_id,
                    "user_id": user_id,
                    "name": tag_data["name"],
                    "color": tag_data["color"],
                    "created_at": current_time,
                    "updated_at": current_time
                }
            }
            
        except Exception as e:
            logger.error(f"创建标签失败: {e}")
            raise Exception(f"创建标签失败: {str(e)}")
    
    async def update_tag(
        self,
        tag_id: str,
        tag_data: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """更新标签"""
        try:
            # 检查标签是否存在且属于当前用户
            existing_response = self.supabase.table("user_tags").select("*").eq("id", tag_id).eq("user_id", user_id).execute()
            
            # 检查响应状态
            if hasattr(existing_response, 'error') and existing_response.error:
                logger.error(f"查询标签失败: {existing_response.error}")
                raise Exception(f"数据库查询失败: {existing_response.error}")
            
            if not existing_response.data:
                raise Exception("标签不存在或无权限修改")
            
            current_time = datetime.utcnow().isoformat()
            
            # 准备更新数据
            update_data = {
                "updated_at": current_time
            }
            
            if "name" in tag_data:
                update_data["name"] = tag_data["name"]
            if "color" in tag_data:
                update_data["color"] = tag_data["color"]
            
            # 更新数据库
            response = self.supabase.table("user_tags").update(update_data).eq("id", tag_id).execute()
            
            # 检查响应状态
            if hasattr(response, 'error') and response.error:
                logger.error(f"更新标签失败: {response.error}")
                raise Exception(f"数据库更新失败: {response.error}")
            
            logger.info(f"成功更新标签: {tag_id}")
            
            # 返回更新后的标签
            updated_tag = existing_response.data[0].copy()
            updated_tag.update(update_data)
            
            return {
                "success": True,
                "message": "标签更新成功",
                "data": updated_tag
            }
            
        except Exception as e:
            logger.error(f"更新标签失败: {e}")
            raise Exception(f"更新标签失败: {str(e)}")
    
    async def delete_tag(self, tag_id: str, user_id: str) -> Dict[str, Any]:
        """删除标签"""
        try:
            # 检查标签是否存在且属于当前用户
            existing_response = self.supabase.table("user_tags").select("id").eq("id", tag_id).eq("user_id", user_id).execute()
            
            # 检查响应状态
            if hasattr(existing_response, 'error') and existing_response.error:
                logger.error(f"查询标签失败: {existing_response.error}")
                raise Exception(f"数据库查询失败: {existing_response.error}")
            
            if not existing_response.data:
                raise Exception("标签不存在或无权限删除")
            
            # 删除标签
            response = self.supabase.table("user_tags").delete().eq("id", tag_id).execute()
            
            # 检查响应状态
            if hasattr(response, 'error') and response.error:
                logger.error(f"删除标签失败: {response.error}")
                raise Exception(f"数据库删除失败: {response.error}")
            
            logger.info(f"成功删除标签: {tag_id}")
            
            return {
                "success": True,
                "message": "标签删除成功"
            }
            
        except Exception as e:
            logger.error(f"删除标签失败: {e}")
            raise Exception(f"删除标签失败: {str(e)}")
    
    async def get_tag_stats(self, user_id: str) -> Dict[str, Any]:
        """获取标签统计信息"""
        try:
            # 获取标签总数
            tags_response = self.supabase.table("user_tags").select("id", count="exact").eq("user_id", user_id).execute()
            total_tags = tags_response.count if hasattr(tags_response, 'count') and tags_response.count is not None else 0
            
            # 获取insights总数
            insights_response = self.supabase.table("insights").select("id", count="exact").eq("user_id", user_id).execute()
            total_insights = insights_response.count if hasattr(insights_response, 'count') and insights_response.count is not None else 0
            
            # 获取最常用的标签（通过insights表中的tags字段统计）
            insights_response = self.supabase.table("insights").select("tags").eq("user_id", user_id).execute()
            
            tag_usage = {}
            if insights_response.data:
                for insight in insights_response.data:
                    if insight.get("tags"):
                        for tag in insight["tags"]:
                            tag_usage[tag] = tag_usage.get(tag, 0) + 1
            
            # 排序获取最常用的标签
            most_used_tags = []
            for tag_name, count in sorted(tag_usage.items(), key=lambda x: x[1], reverse=True)[:5]:
                # 获取标签颜色
                tag_response = self.supabase.table("user_tags").select("color").eq("user_id", user_id).eq("name", tag_name).execute()
                color = tag_response.data[0]["color"] if tag_response.data else "#000000"
                
                most_used_tags.append({
                    "name": tag_name,
                    "count": count,
                    "color": color
                })
            
            # 获取最近创建的标签
            recent_tags_response = self.supabase.table("user_tags").select("name, created_at").eq("user_id", user_id).order("created_at", desc=True).limit(5).execute()
            recent_tags = recent_tags_response.data or []
            
            return {
                "success": True,
                "data": {
                    "total_tags": total_tags,
                    "total_insights": total_insights,
                    "most_used_tags": most_used_tags,
                    "recent_tags": recent_tags
                }
            }
            
        except Exception as e:
            logger.error(f"获取标签统计失败: {e}")
            raise Exception(f"获取标签统计失败: {str(e)}")
    
    async def search_tags(self, query: str, user_id: str) -> Dict[str, Any]:
        """搜索标签"""
        try:
            response = self.supabase.table("user_tags").select("*").eq("user_id", user_id).ilike("name", f"%{query}%").execute()
            
            # 检查响应状态
            if hasattr(response, 'error') and response.error:
                logger.error(f"搜索标签失败: {response.error}")
                raise Exception(f"数据库查询失败: {response.error}")
            
            return {
                "success": True,
                "data": response.data or []
            }
            
        except Exception as e:
            logger.error(f"搜索标签失败: {e}")
            raise Exception(f"搜索标签失败: {str(e)}")
    
    async def add_default_tags_for_user(self, user_id: str) -> Dict[str, Any]:
        """为用户添加默认标签"""
        try:
            from app.services.auth_service import DEFAULT_TAGS
            
            added_tags = []
            skipped_tags = []
            
            for tag in DEFAULT_TAGS:
                try:
                    # 检查标签是否已存在
                    existing_response = self.supabase.table("user_tags").select("id").eq("user_id", user_id).eq("name", tag["name"]).execute()
                    
                    if existing_response.data:
                        skipped_tags.append(tag["name"])
                        continue
                    
                    # 创建新标签
                    await self.create_tag(tag, user_id)
                    added_tags.append(tag["name"])
                    
                except Exception as e:
                    logger.warning(f"添加默认标签 {tag['name']} 失败: {e}")
                    skipped_tags.append(tag["name"])
            
            logger.info(f"为用户 {user_id} 添加默认标签完成: 成功 {len(added_tags)} 个, 跳过 {len(skipped_tags)} 个")
            
            return {
                "success": True,
                "message": f"默认标签添加完成: 成功 {len(added_tags)} 个, 跳过 {len(skipped_tags)} 个",
                "data": {
                    "added_tags": added_tags,
                    "skipped_tags": skipped_tags
                }
            }
            
        except Exception as e:
            logger.error(f"添加默认标签失败: {e}")
            raise Exception(f"添加默认标签失败: {str(e)}")
