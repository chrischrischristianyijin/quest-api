from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime, timedelta
from uuid import UUID

from app.services.memory_service import MemoryService
from app.services.chat_storage_service import ChatStorageService
from app.models.user import UserMemoryProfile, UserMemoryConsolidationRequest
from app.models.chat_storage import MemoryType, ChatMemory

logger = logging.getLogger(__name__)

class MemoryProfileService:
    """用户记忆档案服务 - 自动储存和整合用户记忆到profile中"""
    
    def __init__(self):
        self.memory_service = MemoryService()
        self.chat_storage = ChatStorageService()
    
    async def consolidate_user_memories_to_profile(
        self, 
        user_id: UUID, 
        request: Optional[UserMemoryConsolidationRequest] = None
    ) -> UserMemoryProfile:
        """将用户的所有会话记忆整合到profile中"""
        try:
            # 获取用户的所有会话
            sessions = await self._get_user_sessions(user_id)
            
            if not sessions:
                logger.info(f"用户 {user_id} 没有聊天会话")
                return UserMemoryProfile()
            
            # 收集所有记忆
            all_memories = []
            for session in sessions:
                session_memories = await self.chat_storage.get_session_memories(session['id'])
                all_memories.extend(session_memories)
            
            if not all_memories:
                logger.info(f"用户 {user_id} 没有记忆数据")
                return UserMemoryProfile()
            
            # 按类型分组记忆
            memories_by_type = self._group_memories_by_type(all_memories)
            
            # 整合每种类型的记忆
            consolidated_profile = await self._consolidate_memories_by_type(
                memories_by_type, 
                request
            )
            
            # 更新最后整合时间
            consolidated_profile.last_consolidated = datetime.now()
            
            logger.info(f"用户 {user_id} 记忆整合完成，共整合 {len(all_memories)} 条记忆")
            return consolidated_profile
            
        except Exception as e:
            logger.error(f"整合用户记忆失败: {e}")
            return UserMemoryProfile()
    
    async def auto_consolidate_user_memories(
        self, 
        user_id: UUID, 
        session_id: Optional[UUID] = None
    ) -> Optional[UserMemoryProfile]:
        """自动整合用户记忆（在聊天过程中自动触发）"""
        try:
            # 检查是否需要自动整合
            should_consolidate = await self._should_auto_consolidate(user_id, session_id)
            
            if not should_consolidate:
                return None
            
            # 执行整合
            consolidated_profile = await self.consolidate_user_memories_to_profile(user_id)
            
            # 保存到用户profile
            await self._save_memory_profile_to_user(user_id, consolidated_profile)
            
            return consolidated_profile
            
        except Exception as e:
            logger.error(f"自动整合用户记忆失败: {e}")
            return None
    
    async def get_user_memory_profile(self, user_id: UUID) -> UserMemoryProfile:
        """获取用户的记忆档案"""
        try:
            # 从用户profile中获取记忆档案
            user_profile = await self._get_user_profile(user_id)
            
            if user_profile and user_profile.get('memory_profile'):
                memory_profile_data = user_profile['memory_profile']
                return UserMemoryProfile(**memory_profile_data)
            
            # 如果没有记忆档案，创建一个新的
            return UserMemoryProfile()
            
        except Exception as e:
            logger.error(f"获取用户记忆档案失败: {e}")
            return UserMemoryProfile()
    
    async def update_memory_profile_settings(
        self, 
        user_id: UUID, 
        settings: Dict[str, Any]
    ) -> bool:
        """更新记忆档案设置"""
        try:
            current_profile = await self.get_user_memory_profile(user_id)
            current_profile.consolidation_settings.update(settings)
            
            # 保存更新后的设置
            await self._save_memory_profile_to_user(user_id, current_profile)
            
            logger.info(f"用户 {user_id} 记忆档案设置更新成功")
            return True
            
        except Exception as e:
            logger.error(f"更新记忆档案设置失败: {e}")
            return False
    
    def _group_memories_by_type(self, memories: List[ChatMemory]) -> Dict[str, List[ChatMemory]]:
        """按类型分组记忆"""
        memories_by_type = {
            'preferences': [],
            'facts': [],
            'context': [],
            'insights': []
        }
        
        for memory in memories:
            memory_type = memory.memory_type.value
            if memory_type in memories_by_type:
                memories_by_type[memory_type].append(memory)
        
        return memories_by_type
    
    async def _consolidate_memories_by_type(
        self, 
        memories_by_type: Dict[str, List[ChatMemory]], 
        request: Optional[UserMemoryConsolidationRequest] = None
    ) -> UserMemoryProfile:
        """按类型整合记忆"""
        consolidated_profile = UserMemoryProfile()
        
        # 设置整合参数
        strategy = "similarity"
        threshold = 0.8
        max_memories = 50
        
        if request:
            strategy = request.consolidation_strategy
            if request.memory_types:
                # 只整合指定类型的记忆
                memories_by_type = {
                    k: v for k, v in memories_by_type.items() 
                    if k in request.memory_types
                }
        
        # 整合每种类型的记忆
        for memory_type, memories in memories_by_type.items():
            if not memories:
                continue
            
            # 根据策略整合记忆
            if strategy == "similarity":
                consolidated_memories = await self._consolidate_by_similarity(memories, threshold)
            elif strategy == "importance":
                consolidated_memories = await self._consolidate_by_importance(memories)
            elif strategy == "time":
                consolidated_memories = await self._consolidate_by_time(memories)
            else:
                consolidated_memories = memories
            
            # 限制记忆数量
            if len(consolidated_memories) > max_memories:
                consolidated_memories = consolidated_memories[:max_memories]
            
            # 转换为字典格式存储
            consolidated_dict = {}
            for i, memory in enumerate(consolidated_memories):
                key = f"memory_{i+1}"
                consolidated_dict[key] = {
                    "content": memory.content,
                    "importance": memory.importance_score,
                    "created_at": memory.created_at.isoformat(),
                    "metadata": memory.metadata
                }
            
            # 设置到对应的类型中
            if memory_type == 'user_preference':
                consolidated_profile.preferences = consolidated_dict
            elif memory_type == 'fact':
                consolidated_profile.facts = consolidated_dict
            elif memory_type == 'context':
                consolidated_profile.context = consolidated_dict
            elif memory_type == 'insight':
                consolidated_profile.insights = consolidated_dict
        
        return consolidated_profile
    
    async def _consolidate_by_similarity(
        self, 
        memories: List[ChatMemory], 
        threshold: float
    ) -> List[ChatMemory]:
        """基于相似性整合记忆"""
        try:
            # 使用现有的记忆服务进行整合
            return await self.memory_service.consolidate_memories(memories[0].session_id)
        except Exception as e:
            logger.warning(f"相似性整合失败，使用重要性排序: {e}")
            return await self._consolidate_by_importance(memories)
    
    async def _consolidate_by_importance(self, memories: List[ChatMemory]) -> List[ChatMemory]:
        """基于重要性整合记忆"""
        return sorted(memories, key=lambda x: x.importance_score, reverse=True)
    
    async def _consolidate_by_time(self, memories: List[ChatMemory]) -> List[ChatMemory]:
        """基于时间整合记忆"""
        return sorted(memories, key=lambda x: x.created_at, reverse=True)
    
    async def _should_auto_consolidate(
        self, 
        user_id: UUID, 
        session_id: Optional[UUID] = None
    ) -> bool:
        """判断是否应该自动整合"""
        try:
            # 获取用户记忆档案设置
            profile = await self.get_user_memory_profile(user_id)
            
            # 检查是否启用自动整合
            if not profile.consolidation_settings.get("auto_consolidate", True):
                return False
            
            # 检查距离上次整合的时间
            last_consolidated = profile.last_consolidated
            if last_consolidated:
                time_since_last = datetime.now() - last_consolidated
                # 如果距离上次整合不到1小时，跳过
                if time_since_last < timedelta(hours=1):
                    return False
            
            # 检查是否有新的记忆需要整合
            if session_id:
                session_memories = await self.chat_storage.get_session_memories(session_id)
                if len(session_memories) >= 5:  # 会话中有5条以上记忆时触发整合
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查自动整合条件失败: {e}")
            return False
    
    async def _get_user_sessions(self, user_id: UUID) -> List[Dict[str, Any]]:
        """获取用户的所有会话"""
        try:
            response = self.chat_storage.supabase.table('chat_sessions').select('*').eq('user_id', str(user_id)).eq('is_active', True).execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"获取用户会话失败: {e}")
            return []
    
    async def _get_user_profile(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """获取用户profile"""
        try:
            response = self.chat_storage.supabase.table('profiles').select('*').eq('id', str(user_id)).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"获取用户profile失败: {e}")
            return None
    
    async def _save_memory_profile_to_user(
        self, 
        user_id: UUID, 
        memory_profile: UserMemoryProfile
    ) -> bool:
        """保存记忆档案到用户profile"""
        try:
            # 将记忆档案转换为JSON格式
            memory_profile_dict = memory_profile.dict()
            
            # 更新用户profile
            response = self.chat_storage.supabase.table('profiles').update({
                'memory_profile': memory_profile_dict
            }).eq('id', str(user_id)).execute()
            
            if response.data:
                logger.info(f"用户 {user_id} 记忆档案保存成功")
                return True
            else:
                logger.error(f"保存用户记忆档案失败: {response}")
                return False
                
        except Exception as e:
            logger.error(f"保存记忆档案到用户profile失败: {e}")
            return False
    
    async def get_memory_summary(self, user_id: UUID) -> Dict[str, Any]:
        """获取用户记忆摘要"""
        try:
            profile = await self.get_user_memory_profile(user_id)
            
            summary = {
                "total_memories": 0,
                "by_type": {
                    "preferences": len(profile.preferences),
                    "facts": len(profile.facts),
                    "context": len(profile.context),
                    "insights": len(profile.insights)
                },
                "last_consolidated": profile.last_consolidated.isoformat() if profile.last_consolidated else None,
                "consolidation_settings": profile.consolidation_settings
            }
            
            summary["total_memories"] = sum(summary["by_type"].values())
            
            return summary
            
        except Exception as e:
            logger.error(f"获取记忆摘要失败: {e}")
            return {
                "total_memories": 0,
                "by_type": {"preferences": 0, "facts": 0, "context": 0, "insights": 0},
                "last_consolidated": None,
                "consolidation_settings": {}
            }
