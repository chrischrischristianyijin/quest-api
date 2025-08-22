from typing import List, Optional, Dict, Any
from uuid import UUID
from app.core.database import get_supabase
from app.models.insight import InsightCreate, InsightUpdate, InsightResponse, InsightListResponse
from app.services.insight_tag_service import InsightTagService
import logging

logger = logging.getLogger(__name__)

class InsightsService:
    """Insights服务类"""
    
    @staticmethod
    async def get_insights(
        user_id: UUID,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None,
        target_user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """获取insights列表（分页）"""
        try:
            supabase = get_supabase()
            
            # 确定要查询的用户ID - 如果没有指定target_user_id，默认查询当前用户
            query_user_id = str(target_user_id) if target_user_id else str(user_id)
            
            # 权限检查：如果指定了target_user_id，验证是否为当前用户
            # 如果没有指定target_user_id，则查询当前用户的insights（这是安全的）
            if target_user_id and str(target_user_id) != str(user_id):
                logger.warning(f"用户 {user_id} 尝试访问用户 {target_user_id} 的insights")
                return {
                    "success": False,
                    "message": "只能查看自己的insights"
                }
            
            logger.info(f"查询用户 {query_user_id} 的insights，当前用户: {user_id}")
            
            # 构建查询
            query = supabase.table('insights').select('*').eq('user_id', query_user_id)
            
            # 添加搜索条件
            if search:
                query = query.or_(f'title.ilike.%{search}%,description.ilike.%{search}%')
            
            # 添加排序和分页
            query = query.order('created_at', desc=True).range((page - 1) * limit, page * limit - 1)
            
            # 执行查询
            response = query.execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"获取insights失败: {response.error}")
                return {"success": False, "message": "获取insights失败"}
            
            insights = response.data or []
            logger.info(f"成功获取 {len(insights)} 条insights")
            
            # 获取总数
            count_query = supabase.table('insights').select('id', count='exact').eq('user_id', query_user_id)
            if search:
                count_query = count_query.or_(f'title.ilike.%{search}%,description.ilike.%{search}%')
            
            count_response = count_query.execute()
            total = count_response.count if hasattr(count_response, 'count') else len(insights)
            
            # 批量获取标签
            insight_ids = [UUID(insight['id']) for insight in insights]
            tags_result = await InsightTagService.get_tags_by_insight_ids(insight_ids, user_id)
            
            # 构建响应数据
            insight_responses = []
            for insight in insights:
                insight_tags = tags_result.get('data', {}).get(insight['id'], [])
                
                insight_response = InsightResponse(
                    id=UUID(insight['id']),
                    user_id=UUID(insight['user_id']),
                    title=insight['title'],
                    description=insight['description'],
                    url=insight.get('url'),
                    image_url=insight.get('image_url'),
                    created_at=insight['created_at'],
                    updated_at=insight['updated_at'],
                    tags=insight_tags
                )
                insight_responses.append(insight_response)
            
            return {
                "success": True,
                "data": {
                    "insights": insight_responses,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total,
                        "total_pages": (total + limit - 1) // limit
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"获取insights失败: {str(e)}")
            return {"success": False, "message": f"获取insights失败: {str(e)}"}
    
    @staticmethod
    async def get_all_user_insights(
        user_id: UUID,
        search: Optional[str] = None,
        target_user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """获取用户所有insights（不分页）"""
        try:
            supabase = get_supabase()
            
            # 确定要查询的用户ID - 如果没有指定target_user_id，默认查询当前用户
            query_user_id = str(target_user_id) if target_user_id else str(user_id)
            
            # 权限检查：如果指定了target_user_id，验证是否为当前用户
            # 如果没有指定target_user_id，则查询当前用户的insights（这是安全的）
            if target_user_id and str(target_user_id) != str(user_id):
                logger.warning(f"用户 {user_id} 尝试访问用户 {target_user_id} 的insights")
                return {
                    "success": False,
                    "message": "只能查看自己的insights"
                }
            
            logger.info(f"查询用户 {query_user_id} 的所有insights，当前用户: {user_id}")
            
            # 构建查询
            query = supabase.table('insights').select('*').eq('user_id', query_user_id)
            
            # 添加搜索条件
            if search:
                query = query.or_(f'title.ilike.%{search}%,description.ilike.%{search}%')
            
            # 添加排序
            query = query.order('created_at', desc=True)
            
            # 执行查询
            response = query.execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"获取所有insights失败: {response.error}")
                return {"success": False, "message": "获取所有insights失败"}
            
            insights = response.data or []
            logger.info(f"成功获取 {len(insights)} 条insights")
            
            # 批量获取标签
            insight_ids = [UUID(insight['id']) for insight in insights]
            tags_result = await InsightTagService.get_tags_by_insight_ids(insight_ids, user_id)
            
            # 构建响应数据
            insight_responses = []
            for insight in insights:
                insight_tags = tags_result.get('data', {}).get(insight['id'], [])
                
                insight_response = InsightResponse(
                    id=UUID(insight['id']),
                    user_id=UUID(insight['user_id']),
                    title=insight['title'],
                    description=insight['description'],
                    url=insight.get('url'),
                    image_url=insight.get('image_url'),
                    created_at=insight['created_at'],
                    updated_at=insight['updated_at'],
                    tags=insight_tags
                )
                insight_responses.append(insight_response)
            
            return {
                "success": True,
                "data": {
                    "insights": insight_responses
                }
            }
            
        except Exception as e:
            logger.error(f"获取所有insights失败: {str(e)}")
            return {"success": False, "message": f"获取所有insights失败: {str(e)}"}
    
    @staticmethod
    async def get_insight(insight_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """获取单个insight详情"""
        try:
            supabase = get_supabase()
            
            # 获取insight
            response = supabase.table('insights').select('*').eq('id', str(insight_id)).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"获取insight失败: {response.error}")
                return {"success": False, "message": "获取insight失败"}
            
            if not response.data:
                return {"success": False, "message": "Insight不存在"}
            
            insight = response.data[0]
            
            # 权限检查：只能查看自己的insight
            if insight['user_id'] != str(user_id):
                return {"success": False, "message": "无权查看此insight"}
            
            # 获取标签
            tags_result = await InsightTagService.get_insight_tags(insight_id, user_id)
            insight_tags = tags_result.get('data', []) if tags_result.get('success') else []
            
            # 构建响应数据
            insight_response = InsightResponse(
                id=UUID(insight['id']),
                user_id=UUID(insight['user_id']),
                title=insight['title'],
                description=insight['description'],
                url=insight.get('url'),
                image_url=insight.get('image_url'),
                created_at=insight['created_at'],
                updated_at=insight['updated_at'],
                tags=insight_tags
            )
            
            return {"success": True, "data": insight_response}
            
        except Exception as e:
            logger.error(f"获取insight失败: {str(e)}")
            return {"success": False, "message": f"获取insight失败: {str(e)}"}
    
    @staticmethod
    async def create_insight(insight_data: InsightCreate, user_id: UUID) -> Dict[str, Any]:
        """创建新insight"""
        try:
            supabase = get_supabase()
            
            # 准备insight数据（不包含tags）
            insight_insert_data = {
                'title': insight_data.title,
                'description': insight_data.description,
                'url': insight_data.url,
                'image_url': insight_data.image_url,
                'user_id': str(user_id)
            }
            
            # 创建insight
            response = supabase.table('insights').insert(insight_insert_data).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"创建insight失败: {response.error}")
                return {"success": False, "message": "创建insight失败"}
            
            if not response.data:
                return {"success": False, "message": "创建insight失败"}
            
            insight = response.data[0]
            insight_id = UUID(insight['id'])
            
            # 处理标签
            if insight_data.tag_names:
                tags_result = await InsightTagService.update_insight_tags(
                    insight_id, insight_data.tag_names, user_id
                )
                if not tags_result.get('success'):
                    logger.warning(f"创建insight成功，但标签处理失败: {tags_result.get('message')}")
            
            # 获取完整的insight数据（包含标签）
            return await InsightsService.get_insight(insight_id, user_id)
            
        except Exception as e:
            logger.error(f"创建insight失败: {str(e)}")
            return {"success": False, "message": f"创建insight失败: {str(e)}"}
    
    @staticmethod
    async def update_insight(insight_id: UUID, insight_data: InsightUpdate, user_id: UUID) -> Dict[str, Any]:
        """更新insight"""
        try:
            supabase = get_supabase()
            
            # 检查insight是否存在且属于该用户
            existing_response = supabase.table('insights').select('user_id').eq('id', str(insight_id)).execute()
            
            if hasattr(existing_response, 'error') and existing_response.error:
                logger.error(f"检查insight失败: {existing_response.error}")
                return {"success": False, "message": "检查insight失败"}
            
            if not existing_response.data:
                return {"success": False, "message": "Insight不存在"}
            
            if existing_response.data[0]['user_id'] != str(user_id):
                return {"success": False, "message": "无权更新此insight"}
            
            # 准备更新数据（不包含tags）
            update_data = {}
            if insight_data.title is not None:
                update_data['title'] = insight_data.title
            if insight_data.description is not None:
                update_data['description'] = insight_data.description
            if insight_data.url is not None:
                update_data['url'] = insight_data.url
            if insight_data.image_url is not None:
                update_data['image_url'] = insight_data.image_url
            
            # 更新insight
            if update_data:
                response = supabase.table('insights').update(update_data).eq('id', str(insight_id)).execute()
                
                if hasattr(response, 'error') and response.error:
                    logger.error(f"更新insight失败: {response.error}")
                    return {"success": False, "message": "更新insight失败"}
            
            # 处理标签更新
            if insight_data.tag_names is not None:
                tags_result = await InsightTagService.update_insight_tags(
                    insight_id, insight_data.tag_names, user_id
                )
                if not tags_result.get('success'):
                    logger.warning(f"更新insight成功，但标签处理失败: {tags_result.get('message')}")
            
            # 获取更新后的insight数据
            return await InsightsService.get_insight(insight_id, user_id)
            
        except Exception as e:
            logger.error(f"更新insight失败: {str(e)}")
            return {"success": False, "message": f"更新insight失败: {str(e)}"}
    
    @staticmethod
    async def delete_insight(insight_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """删除insight"""
        try:
            supabase = get_supabase()
            
            # 检查insight是否存在且属于该用户
            existing_response = supabase.table('insights').select('user_id').eq('id', str(insight_id)).execute()
            
            if hasattr(existing_response, 'error') and existing_response.error:
                logger.error(f"检查insight失败: {existing_response.error}")
                return {"success": False, "message": "检查insight失败"}
            
            if not existing_response.data:
                return {"success": False, "message": "Insight不存在"}
            
            if existing_response.data[0]['user_id'] != str(user_id):
                return {"success": False, "message": "无权删除此insight"}
            
            # 删除insight（标签关联会通过CASCADE自动删除）
            response = supabase.table('insights').delete().eq('id', str(insight_id)).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"删除insight失败: {response.error}")
                return {"success": False, "message": "删除insight失败"}
            
            return {"success": True, "message": "Insight删除成功"}
            
        except Exception as e:
            logger.error(f"删除insight失败: {str(e)}")
            return {"success": False, "message": f"删除insight失败: {str(e)}"}
