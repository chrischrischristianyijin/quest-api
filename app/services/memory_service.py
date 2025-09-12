from typing import List, Optional, Dict, Any
import logging
import os
import httpx
import json
from datetime import datetime
from uuid import UUID

from app.services.chat_storage_service import ChatStorageService
from app.models.chat_storage import ChatMemoryCreate, ChatMemory, MemoryType

logger = logging.getLogger(__name__)

class MemoryService:
    """记忆管理服务 - 实现ChatGPT的记忆功能"""
    
    def __init__(self):
        self.chat_storage = ChatStorageService()
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.chat_model = os.getenv('CHAT_MODEL', 'gpt-4o-mini')
    
    async def extract_memories_from_conversation(
        self, 
        conversation_history: List[Dict[str, str]], 
        session_id: UUID
    ) -> List[ChatMemoryCreate]:
        """从对话历史中提取记忆"""
        try:
            if not self.openai_api_key:
                logger.warning("OpenAI API Key未配置，跳过记忆提取")
                return []
            
            # 构建记忆提取提示
            conversation_text = self._format_conversation_for_memory_extraction(conversation_history)
            
            memory_prompt = f"""
请从以下对话中提取重要的记忆信息。记忆应该包括：
1. 用户偏好和习惯
2. 重要的事实信息
3. 上下文信息（如当前项目、任务等）
4. 有价值的洞察

对话内容：
{conversation_text}

请以JSON格式返回记忆，每个记忆包含：
- type: 记忆类型 (user_preference, fact, context, insight)
- content: 记忆内容
- importance: 重要性分数 (0.0-1.0)

返回格式：
{{
    "memories": [
        {{
            "type": "user_preference",
            "content": "用户喜欢在早上工作",
            "importance": 0.8
        }}
    ]
}}
"""
            
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json',
            }
            
            # 根据模型类型设置不同的参数
            if 'gpt-5' in self.chat_model.lower():
                # GPT-5 mini 特殊参数
                payload = {
                    'model': self.chat_model,
                    'messages': [
                        {"role": "user", "content": memory_prompt}
                    ],
                    'temperature': 0.1,
                    'max_completion_tokens': 1000,  # GPT-5 mini 使用 max_completion_tokens
                    'verbosity': 'low',  # 简短回答
                    'reasoning_effort': 'minimal'  # 快速推理
                }
            else:
                # 标准 GPT 模型参数
                payload = {
                    'model': self.chat_model,
                    'messages': [
                        {"role": "user", "content": memory_prompt}
                    ],
                    'temperature': 0.1,
                    'max_tokens': 1000
                }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.openai_base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                memory_text = data['choices'][0]['message']['content']
                
                # 解析JSON响应
                memories_data = json.loads(memory_text)
                memories = []
                
                for memory_data in memories_data.get('memories', []):
                    memories.append(ChatMemoryCreate(
                        session_id=session_id,
                        memory_type=MemoryType(memory_data['type']),
                        content=memory_data['content'],
                        importance_score=memory_data['importance'],
                        metadata={
                            'extracted_at': datetime.now().isoformat(),
                            'source': 'conversation_analysis'
                        }
                    ))
                
                logger.info(f"从对话中提取了 {len(memories)} 个记忆")
                return memories
                
        except Exception as e:
            logger.error(f"提取记忆失败: {e}")
            return []
    
    async def create_memories(self, memories: List[ChatMemoryCreate]) -> List[ChatMemory]:
        """批量创建记忆"""
        created_memories = []
        for memory_data in memories:
            try:
                memory = await self.chat_storage.create_memory(memory_data)
                created_memories.append(memory)
            except Exception as e:
                logger.warning(f"创建记忆失败: {e}")
                continue
        
        return created_memories
    
    async def get_relevant_memories(
        self, 
        session_id: UUID, 
        query: str, 
        limit: int = 5
    ) -> List[ChatMemory]:
        """获取与查询相关的记忆"""
        try:
            # 获取会话的所有记忆
            all_memories = await self.chat_storage.get_session_memories(session_id)
            
            if not all_memories:
                return []
            
            # 使用AI计算记忆相关性
            relevant_memories = await self._rank_memories_by_relevance(all_memories, query)
            
            # 返回最相关的记忆
            return relevant_memories[:limit]
            
        except Exception as e:
            logger.error(f"获取相关记忆失败: {e}")
            return []
    
    async def _rank_memories_by_relevance(
        self, 
        memories: List[ChatMemory], 
        query: str
    ) -> List[ChatMemory]:
        """使用AI对记忆进行相关性排序"""
        try:
            if not self.openai_api_key or len(memories) <= 1:
                # 如果没有API key或记忆很少，按重要性排序
                return sorted(memories, key=lambda x: x.importance_score, reverse=True)
            
            # 构建记忆列表
            memories_text = "\n".join([
                f"{i+1}. [{mem.memory_type.value}] {mem.content} (重要性: {mem.importance_score})"
                for i, mem in enumerate(memories)
            ])
            
            ranking_prompt = f"""
请根据以下查询，对记忆进行相关性排序。

查询: {query}

记忆列表:
{memories_text}

请返回最相关的记忆编号（用逗号分隔），按相关性从高到低排序。
例如: 3,1,5,2,4

只返回数字，不要其他内容。
"""
            
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json',
            }
            
            # 根据模型类型设置不同的参数
            if 'gpt-5' in self.chat_model.lower():
                # GPT-5 mini 特殊参数
                payload = {
                    'model': self.chat_model,
                    'messages': [
                        {"role": "user", "content": ranking_prompt}
                    ],
                    'temperature': 0.1,
                    'max_completion_tokens': 50,  # GPT-5 mini 使用 max_completion_tokens
                    'verbosity': 'low',  # 简短回答
                    'reasoning_effort': 'minimal'  # 快速推理
                }
            else:
                # 标准 GPT 模型参数
                payload = {
                    'model': self.chat_model,
                    'messages': [
                        {"role": "user", "content": ranking_prompt}
                    ],
                    'temperature': 0.1,
                    'max_tokens': 50
                }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.openai_base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                ranking_text = data['choices'][0]['message']['content'].strip()
                
                # 解析排序结果
                try:
                    ranked_indices = [int(x.strip()) - 1 for x in ranking_text.split(',')]
                    ranked_memories = []
                    
                    for idx in ranked_indices:
                        if 0 <= idx < len(memories):
                            ranked_memories.append(memories[idx])
                    
                    # 添加未排序的记忆
                    for i, memory in enumerate(memories):
                        if i not in ranked_indices:
                            ranked_memories.append(memory)
                    
                    return ranked_memories
                    
                except (ValueError, IndexError):
                    # 如果解析失败，按重要性排序
                    return sorted(memories, key=lambda x: x.importance_score, reverse=True)
                
        except Exception as e:
            logger.error(f"记忆排序失败: {e}")
            # 回退到按重要性排序
            return sorted(memories, key=lambda x: x.importance_score, reverse=True)
    
    def _format_conversation_for_memory_extraction(self, conversation_history: List[Dict[str, str]]) -> str:
        """格式化对话历史用于记忆提取"""
        formatted_lines = []
        for msg in conversation_history[-10:]:  # 只取最近10条消息
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            formatted_lines.append(f"{role}: {content}")
        
        return "\n".join(formatted_lines)
    
    async def update_memory_importance(
        self, 
        memory_id: UUID, 
        new_importance: float
    ) -> Optional[ChatMemory]:
        """更新记忆的重要性分数"""
        try:
            from app.models.chat_storage import ChatMemoryUpdate
            
            update_data = ChatMemoryUpdate(importance_score=new_importance)
            return await self.chat_storage.update_memory(memory_id, update_data)
            
        except Exception as e:
            logger.error(f"更新记忆重要性失败: {e}")
            return None
    
    async def consolidate_memories(self, session_id: UUID) -> List[ChatMemory]:
        """合并相似的记忆"""
        try:
            memories = await self.chat_storage.get_session_memories(session_id)
            
            if len(memories) < 2:
                return memories
            
            # 按类型分组
            memories_by_type = {}
            for memory in memories:
                memory_type = memory.memory_type
                if memory_type not in memories_by_type:
                    memories_by_type[memory_type] = []
                memories_by_type[memory_type].append(memory)
            
            consolidated_memories = []
            
            # 对每种类型的记忆进行合并
            for memory_type, type_memories in memories_by_type.items():
                if len(type_memories) <= 1:
                    consolidated_memories.extend(type_memories)
                    continue
                
                # 使用AI合并相似记忆
                merged_memories = await self._merge_similar_memories(type_memories)
                consolidated_memories.extend(merged_memories)
            
            return consolidated_memories
            
        except Exception as e:
            logger.error(f"合并记忆失败: {e}")
            return memories
    
    async def _merge_similar_memories(self, memories: List[ChatMemory]) -> List[ChatMemory]:
        """合并相似的记忆"""
        try:
            if not self.openai_api_key or len(memories) <= 1:
                return memories
            
            # 构建记忆列表
            memories_text = "\n".join([
                f"{i+1}. {mem.content} (重要性: {mem.importance_score})"
                for i, mem in enumerate(memories)
            ])
            
            merge_prompt = f"""
请分析以下记忆，找出可以合并的相似记忆。

记忆列表:
{memories_text}

请返回合并后的记忆，格式：
{{
    "merged_memories": [
        {{
            "content": "合并后的记忆内容",
            "importance": 0.8
        }}
    ]
}}

如果记忆无法合并，请保持原样。
"""
            
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json',
            }
            
            # 根据模型类型设置不同的参数
            if 'gpt-5' in self.chat_model.lower():
                # GPT-5 mini 特殊参数
                payload = {
                    'model': self.chat_model,
                    'messages': [
                        {"role": "user", "content": merge_prompt}
                    ],
                    'temperature': 0.1,
                    'max_completion_tokens': 800,  # GPT-5 mini 使用 max_completion_tokens
                    'verbosity': 'low',  # 简短回答
                    'reasoning_effort': 'minimal'  # 快速推理
                }
            else:
                # 标准 GPT 模型参数
                payload = {
                    'model': self.chat_model,
                    'messages': [
                        {"role": "user", "content": merge_prompt}
                    ],
                    'temperature': 0.1,
                    'max_tokens': 800
                }
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.openai_base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                merge_text = data['choices'][0]['message']['content']
                
                # 解析合并结果
                merge_data = json.loads(merge_text)
                merged_memories = []
                
                for merged_memory_data in merge_data.get('merged_memories', []):
                    # 创建新的记忆对象（这里简化处理）
                    merged_memories.append(memories[0])  # 使用第一个记忆作为模板
                
                return merged_memories if merged_memories else memories
                
        except Exception as e:
            logger.error(f"合并记忆失败: {e}")
            return memories
