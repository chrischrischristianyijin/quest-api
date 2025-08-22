from typing import List, Optional
from uuid import UUID
from app.core.database import get_supabase
import logging

logger = logging.getLogger(__name__)

class InsightTagService:
    """Insight标签关联服务 - 简化版本"""
    
    @staticmethod
    async def update_insight_tags(insight_id: UUID, tag_names: List[str], user_id: UUID) -> dict:
        """更新insight的标签（替换现有标签）"""
        try:
            supabase = get_supabase()
            
            # 检查insight是否属于该用户
            insight_response = supabase.table('insights').select('user_id').eq('id', str(insight_id)).execute()
            if hasattr(insight_response, 'error') and insight_response.error:
                return {"success": False, "message": "Insight不存在"}
            
            if not insight_response.data:
                return {"success": False, "message": "Insight不存在"}
            
            if insight_response.data[0]['user_id'] != str(user_id):
                return {"success": False, "message": "无权操作此insight"}
            
            # 删除现有标签关联
            delete_response = supabase.table('insight_tags').delete().eq('insight_id', str(insight_id)).execute()
            if hasattr(delete_response, 'error') and delete_response.error:
                logger.error(f"删除现有标签关联失败: {delete_response.error}")
                return {"success": False, "message": "更新标签失败"}
            
            # 创建新的标签关联
            if tag_names:
                for tag_name in tag_names:
                    # 查找或创建标签
                    tag_response = supabase.table('user_tags').select('id').eq('name', tag_name).eq('user_id', str(user_id)).execute()
                    
                    if hasattr(tag_response, 'error') and tag_response.error:
                        continue
                    
                    if tag_response.data:
                        tag_id = tag_response.data[0]['id']
                    else:
                        # 创建新标签（使用默认颜色）
                        new_tag_response = supabase.table('user_tags').insert({
                            'name': tag_name,
                            'color': '#FF5733',  # 默认颜色
                            'user_id': str(user_id)
                        }).execute()
                        
                        if hasattr(new_tag_response, 'error') and new_tag_response.error:
                            continue
                        
                        tag_id = new_tag_response.data[0]['id']
                    
                    # 创建标签关联
                    supabase.table('insight_tags').insert({
                        'insight_id': str(insight_id),
                        'tag_id': tag_id,
                        'user_id': str(user_id)
                    }).execute()
            
            return {"success": True, "message": "标签更新成功"}
            
        except Exception as e:
            logger.error(f"更新insight标签失败: {str(e)}")
            return {"success": False, "message": f"更新标签失败: {str(e)}"}
    
    @staticmethod
    async def get_tags_by_insight_ids(insight_ids: List[UUID], user_id: UUID) -> dict:
        """批量获取多个insight的标签"""
        try:
            supabase = get_supabase()
            
            if not insight_ids:
                return {"success": True, "data": {}}
            
            # 获取所有相关insight的标签
            response = supabase.table('insight_tags').select(
                'insight_id, tag_id, user_tags(name, color)'
            ).in_('insight_id', [str(id) for id in insight_ids]).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"批量获取insight标签失败: {response.error}")
                return {"success": False, "message": "获取标签失败"}
            
            # 按insight_id分组标签
            tags_by_insight = {}
            for item in response.data:
                insight_id = item['insight_id']
                if insight_id not in tags_by_insight:
                    tags_by_insight[insight_id] = []
                
                if item.get('user_tags'):
                    tags_by_insight[insight_id].append({
                        'tag_id': item['tag_id'],
                        'name': item['user_tags']['name'],
                        'color': item['user_tags']['color']
                    })
            
            return {"success": True, "data": tags_by_insight}
            
        except Exception as e:
            logger.error(f"批量获取insight标签失败: {str(e)}")
            return {"success": False, "message": f"获取标签失败: {str(e)}"}
    
    @staticmethod
    async def get_insight_tags(insight_id: UUID, user_id: UUID) -> dict:
        """获取单个insight的所有标签"""
        try:
            supabase = get_supabase()
            
            # 检查insight是否属于该用户
            insight_response = supabase.table('insights').select('user_id').eq('id', str(insight_id)).execute()
            if hasattr(insight_response, 'error') and insight_response.error:
                return {"success": False, "message": "Insight不存在"}
            
            if not insight_response.data:
                return {"success": False, "message": "Insight不存在"}
            
            if insight_response.data[0]['user_id'] != str(user_id):
                return {"success": False, "message": "无权查看此insight"}
            
            # 获取标签关联
            response = supabase.table('insight_tags').select(
                'id, tag_id, created_at, user_tags(name, color)'
            ).eq('insight_id', str(insight_id)).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"获取insight标签失败: {response.error}")
                return {"success": False, "message": "获取标签失败"}
            
            # 格式化标签数据
            tags = []
            for item in response.data:
                if item.get('user_tags'):
                    tags.append({
                        'id': item['id'],
                        'tag_id': item['tag_id'],
                        'tag_name': item['user_tags']['name'],
                        'tag_color': item['user_tags']['color'],
                        'created_at': item['created_at']
                    })
            
            return {"success": True, "data": tags}
            
        except Exception as e:
            logger.error(f"获取insight标签失败: {str(e)}")
            return {"success": False, "message": f"获取标签失败: {str(e)}"}
