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
        """批量获取多个insight的标签（优化版本，支持分批处理）"""
        try:
            supabase = get_supabase()
            
            if not insight_ids:
                return {"success": True, "data": {}}
            
            # 性能优化：大批量数据自动分批处理
            BATCH_SIZE = 200  # 每批处理200个
            all_tags_by_insight = {}
            
            if len(insight_ids) > BATCH_SIZE:
                logger.info(f"大批量标签查询 ({len(insight_ids)})，自动分批处理")
                
                # 分批处理
                for i in range(0, len(insight_ids), BATCH_SIZE):
                    batch_ids = insight_ids[i:i + BATCH_SIZE]
                    batch_result = await InsightTagService._get_tags_batch(batch_ids, user_id, supabase)
                    if batch_result.get('success'):
                        all_tags_by_insight.update(batch_result.get('data', {}))
                    else:
                        logger.warning(f"批次 {i//BATCH_SIZE + 1} 标签查询失败")
                
                return {"success": True, "data": all_tags_by_insight}
            else:
                # 单批处理
                return await InsightTagService._get_tags_batch(insight_ids, user_id, supabase)
            
        except Exception as e:
            logger.error(f"批量获取insight标签失败: {str(e)}")
            return {"success": False, "message": f"获取标签失败: {str(e)}"}
    
    @staticmethod
    async def _get_tags_batch(insight_ids: List[UUID], user_id: UUID, supabase) -> dict:
        """单批次获取标签（内部方法）"""
        try:
            # 转换为字符串列表，减少重复转换
            insight_id_strings = [str(id) for id in insight_ids]
            
            # 获取所有相关insight的标签 - 优化查询，只选择必要字段
            response = supabase.table('insight_tags').select(
                'insight_id, user_tags!inner(id, name, color)'
            ).in_('insight_id', insight_id_strings).eq('user_id', str(user_id)).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"批量获取insight标签失败: {response.error}")
                return {"success": False, "message": "获取标签失败"}
            
            # 按insight_id分组标签 - 优化数据结构构建
            tags_by_insight = {}
            for item in response.data or []:
                insight_id = item['insight_id']
                if insight_id not in tags_by_insight:
                    tags_by_insight[insight_id] = []
                
                if item.get('user_tags'):
                    tag_data = item['user_tags']
                    tags_by_insight[insight_id].append({
                        'id': tag_data['id'],
                        'name': tag_data['name'],
                        'color': tag_data['color']
                    })
            
            return {"success": True, "data": tags_by_insight}
            
        except Exception as e:
            logger.error(f"单批次获取标签失败: {str(e)}")
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

    @staticmethod
    async def update_insight_tags_by_ids(insight_id: UUID, tag_ids: List[UUID], user_id: UUID) -> dict:
        """通过标签ID更新insight的标签（替换现有标签）"""
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
            
            # 验证所有标签是否属于该用户
            if tag_ids:
                tags_response = supabase.table('user_tags').select('id').in_('id', [str(tag_id) for tag_id in tag_ids]).eq('user_id', str(user_id)).execute()
                if hasattr(tags_response, 'error') and tags_response.error:
                    return {"success": False, "message": "验证标签失败"}
                
                valid_tag_ids = [str(tag['id']) for tag in tags_response.data]
                invalid_tag_ids = [str(tag_id) for tag_id in tag_ids if str(tag_id) not in valid_tag_ids]
                
                if invalid_tag_ids:
                    return {"success": False, "message": f"以下标签不存在或无权限: {invalid_tag_ids}"}
            
            # 删除现有标签关联
            delete_response = supabase.table('insight_tags').delete().eq('insight_id', str(insight_id)).execute()
            if hasattr(delete_response, 'error') and delete_response.error:
                logger.error(f"删除现有标签关联失败: {delete_response.error}")
                return {"success": False, "message": "更新标签失败"}
            
            # 创建新的标签关联
            if tag_ids:
                for tag_id in tag_ids:
                    # 直接创建标签关联（标签已存在且已验证权限）
                    supabase.table('insight_tags').insert({
                        'insight_id': str(insight_id),
                        'tag_id': str(tag_id),
                        'user_id': str(user_id)
                    }).execute()
            
            return {"success": True, "message": "标签更新成功"}
            
        except Exception as e:
            logger.error(f"通过ID更新insight标签失败: {str(e)}")
            return {"success": False, "message": f"更新标签失败: {str(e)}"}
