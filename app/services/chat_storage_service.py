from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from uuid import UUID

from app.core.database import get_supabase_service
from app.models.chat_storage import (
    ChatSession, ChatSessionCreate, ChatSessionUpdate, ChatSessionOverview,
    ChatMessage, ChatMessageCreate,
    ChatRAGContext, ChatRAGContextCreate,
    ChatMemory, ChatMemoryCreate, ChatMemoryUpdate,
    ChatSessionWithMessages, ChatMessageWithContext, ChatContextResponse,
    MessageRole, MemoryType
)

logger = logging.getLogger(__name__)

class ChatStorageService:
    """聊天存储服务"""
    
    def __init__(self):
        self.supabase = get_supabase_service()
    
    # 会话管理
    async def create_session(self, session_data: ChatSessionCreate) -> ChatSession:
        """创建聊天会话"""
        try:
            response = self.supabase.table('chat_sessions').insert({
                'user_id': str(session_data.user_id),
                'title': session_data.title,
                'metadata': session_data.metadata or {}
            }).execute()
            
            if response.data:
                session_data_dict = response.data[0]
                return ChatSession(
                    id=UUID(session_data_dict['id']),
                    user_id=UUID(session_data_dict['user_id']),
                    title=session_data_dict.get('title'),
                    created_at=datetime.fromisoformat(session_data_dict['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(session_data_dict['updated_at'].replace('Z', '+00:00')),
                    is_active=session_data_dict.get('is_active', True),
                    metadata=session_data_dict.get('metadata', {})
                )
            else:
                raise Exception("创建会话失败")
                
        except Exception as e:
            logger.error(f"创建聊天会话失败: {e}")
            raise
    
    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        """获取聊天会话"""
        try:
            response = self.supabase.table('chat_sessions').select('*').eq('id', str(session_id)).execute()
            
            if response.data:
                session_data = response.data[0]
                return ChatSession(
                    id=UUID(session_data['id']),
                    user_id=UUID(session_data['user_id']),
                    title=session_data.get('title'),
                    created_at=datetime.fromisoformat(session_data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(session_data['updated_at'].replace('Z', '+00:00')),
                    is_active=session_data.get('is_active', True),
                    metadata=session_data.get('metadata', {})
                )
            return None
            
        except Exception as e:
            logger.error(f"获取聊天会话失败: {e}")
            raise
    
    async def get_user_sessions(self, user_id: UUID, page: int = 1, size: int = 20) -> List[ChatSessionOverview]:
        """获取用户的会话列表"""
        try:
            offset = (page - 1) * size
            response = self.supabase.table('chat_session_overview').select('*').eq('user_id', str(user_id)).order('updated_at', desc=True).range(offset, offset + size - 1).execute()
            
            sessions = []
            for session_data in response.data or []:
                sessions.append(ChatSessionOverview(
                    id=UUID(session_data['id']),
                    user_id=UUID(session_data['user_id']),
                    title=session_data.get('title'),
                    created_at=datetime.fromisoformat(session_data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(session_data['updated_at'].replace('Z', '+00:00')),
                    is_active=session_data.get('is_active', True),
                    message_count=session_data.get('message_count', 0),
                    last_message_at=datetime.fromisoformat(session_data['last_message_at'].replace('Z', '+00:00')) if session_data.get('last_message_at') else None
                ))
            
            return sessions
            
        except Exception as e:
            logger.error(f"获取用户会话列表失败: {e}")
            raise
    
    async def update_session(self, session_id: UUID, update_data: ChatSessionUpdate) -> Optional[ChatSession]:
        """更新聊天会话"""
        try:
            update_dict = {}
            if update_data.title is not None:
                update_dict['title'] = update_data.title
            if update_data.is_active is not None:
                update_dict['is_active'] = update_data.is_active
            if update_data.metadata is not None:
                update_dict['metadata'] = update_data.metadata
            
            if not update_dict:
                return await self.get_session(session_id)
            
            response = self.supabase.table('chat_sessions').update(update_dict).eq('id', str(session_id)).execute()
            
            if response.data:
                session_data = response.data[0]
                return ChatSession(
                    id=UUID(session_data['id']),
                    user_id=UUID(session_data['user_id']),
                    title=session_data.get('title'),
                    created_at=datetime.fromisoformat(session_data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(session_data['updated_at'].replace('Z', '+00:00')),
                    is_active=session_data.get('is_active', True),
                    metadata=session_data.get('metadata', {})
                )
            return None
            
        except Exception as e:
            logger.error(f"更新聊天会话失败: {e}")
            raise
    
    # 消息管理
    async def create_message(self, message_data: ChatMessageCreate) -> ChatMessage:
        """创建聊天消息"""
        try:
            response = self.supabase.table('chat_messages').insert({
                'session_id': str(message_data.session_id),
                'role': message_data.role.value,
                'content': message_data.content,
                'metadata': message_data.metadata or {},
                'parent_message_id': str(message_data.parent_message_id) if message_data.parent_message_id else None
            }).execute()
            
            if response.data:
                message_data_dict = response.data[0]
                return ChatMessage(
                    id=UUID(message_data_dict['id']),
                    session_id=UUID(message_data_dict['session_id']),
                    role=MessageRole(message_data_dict['role']),
                    content=message_data_dict['content'],
                    created_at=datetime.fromisoformat(message_data_dict['created_at'].replace('Z', '+00:00')),
                    metadata=message_data_dict.get('metadata', {}),
                    parent_message_id=UUID(message_data_dict['parent_message_id']) if message_data_dict.get('parent_message_id') else None
                )
            else:
                raise Exception("创建消息失败")
                
        except Exception as e:
            logger.error(f"创建聊天消息失败: {e}")
            raise
    
    async def get_session_messages(self, session_id: UUID, limit: int = 50) -> List[ChatMessageWithContext]:
        """获取会话的消息列表"""
        try:
            response = self.supabase.table('chat_messages').select('*, chat_rag_contexts(*)').eq('session_id', str(session_id)).order('created_at', desc=False).limit(limit).execute()
            
            messages = []
            for message_data in response.data or []:
                # 处理RAG上下文
                rag_context = None
                if message_data.get('chat_rag_contexts'):
                    rag_data = message_data['chat_rag_contexts'][0]
                    rag_context = ChatRAGContext(
                        id=UUID(rag_data['id']),
                        message_id=UUID(rag_data['message_id']),
                        rag_chunks=rag_data.get('rag_chunks', []),
                        context_text=rag_data.get('context_text'),
                        total_context_tokens=rag_data.get('total_context_tokens', 0),
                        extracted_keywords=rag_data.get('extracted_keywords'),
                        rag_k=rag_data.get('rag_k', 10),
                        rag_min_score=rag_data.get('rag_min_score', 0.25),
                        created_at=datetime.fromisoformat(rag_data['created_at'].replace('Z', '+00:00'))
                    )
                
                messages.append(ChatMessageWithContext(
                    id=UUID(message_data['id']),
                    session_id=UUID(message_data['session_id']),
                    role=MessageRole(message_data['role']),
                    content=message_data['content'],
                    created_at=datetime.fromisoformat(message_data['created_at'].replace('Z', '+00:00')),
                    metadata=message_data.get('metadata', {}),
                    parent_message_id=UUID(message_data['parent_message_id']) if message_data.get('parent_message_id') else None,
                    rag_context=rag_context
                ))
            
            return messages
            
        except Exception as e:
            logger.error(f"获取会话消息失败: {e}")
            raise
    
    # RAG上下文管理
    async def create_rag_context(self, context_data: ChatRAGContextCreate) -> ChatRAGContext:
        """创建RAG上下文"""
        try:
            # 转换RAG分块为JSON格式
            rag_chunks_json = [chunk.dict() for chunk in context_data.rag_chunks]
            
            response = self.supabase.table('chat_rag_contexts').insert({
                'message_id': str(context_data.message_id),
                'rag_chunks': rag_chunks_json,
                'context_text': context_data.context_text,
                'total_context_tokens': context_data.total_context_tokens,
                'extracted_keywords': context_data.extracted_keywords,
                'rag_k': context_data.rag_k,
                'rag_min_score': context_data.rag_min_score
            }).execute()
            
            if response.data:
                context_data_dict = response.data[0]
                return ChatRAGContext(
                    id=UUID(context_data_dict['id']),
                    message_id=UUID(context_data_dict['message_id']),
                    rag_chunks=context_data.rag_chunks,
                    context_text=context_data_dict.get('context_text'),
                    total_context_tokens=context_data_dict.get('total_context_tokens', 0),
                    extracted_keywords=context_data_dict.get('extracted_keywords'),
                    rag_k=context_data_dict.get('rag_k', 10),
                    rag_min_score=context_data_dict.get('rag_min_score', 0.25),
                    created_at=datetime.fromisoformat(context_data_dict['created_at'].replace('Z', '+00:00'))
                )
            else:
                raise Exception("创建RAG上下文失败")
                
        except Exception as e:
            logger.error(f"创建RAG上下文失败: {e}")
            raise
    
    # 记忆管理
    async def create_memory(self, memory_data: ChatMemoryCreate) -> ChatMemory:
        """创建聊天记忆"""
        try:
            response = self.supabase.table('chat_memories').insert({
                'session_id': str(memory_data.session_id),
                'memory_type': memory_data.memory_type.value,
                'content': memory_data.content,
                'importance_score': memory_data.importance_score,
                'metadata': memory_data.metadata or {}
            }).execute()
            
            if response.data:
                memory_data_dict = response.data[0]
                return ChatMemory(
                    id=UUID(memory_data_dict['id']),
                    session_id=UUID(memory_data_dict['session_id']),
                    memory_type=MemoryType(memory_data_dict['memory_type']),
                    content=memory_data_dict['content'],
                    importance_score=memory_data_dict.get('importance_score', 0.5),
                    created_at=datetime.fromisoformat(memory_data_dict['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(memory_data_dict['updated_at'].replace('Z', '+00:00')),
                    is_active=memory_data_dict.get('is_active', True),
                    metadata=memory_data_dict.get('metadata', {})
                )
            else:
                raise Exception("创建记忆失败")
                
        except Exception as e:
            logger.error(f"创建聊天记忆失败: {e}")
            raise
    
    async def get_session_memories(self, session_id: UUID, memory_types: Optional[List[MemoryType]] = None) -> List[ChatMemory]:
        """获取会话的记忆"""
        try:
            query = self.supabase.table('chat_memories').select('*').eq('session_id', str(session_id)).eq('is_active', True)
            
            if memory_types:
                query = query.in_('memory_type', [mt.value for mt in memory_types])
            
            response = query.order('importance_score', desc=True).execute()
            
            memories = []
            for memory_data in response.data or []:
                memories.append(ChatMemory(
                    id=UUID(memory_data['id']),
                    session_id=UUID(memory_data['session_id']),
                    memory_type=MemoryType(memory_data['memory_type']),
                    content=memory_data['content'],
                    importance_score=memory_data.get('importance_score', 0.5),
                    created_at=datetime.fromisoformat(memory_data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(memory_data['updated_at'].replace('Z', '+00:00')),
                    is_active=memory_data.get('is_active', True),
                    metadata=memory_data.get('metadata', {})
                ))
            
            return memories
            
        except Exception as e:
            logger.error(f"获取会话记忆失败: {e}")
            raise
    
    async def update_memory(self, memory_id: UUID, update_data: ChatMemoryUpdate) -> Optional[ChatMemory]:
        """更新聊天记忆"""
        try:
            update_dict = {}
            if update_data.content is not None:
                update_dict['content'] = update_data.content
            if update_data.importance_score is not None:
                update_dict['importance_score'] = update_data.importance_score
            if update_data.is_active is not None:
                update_dict['is_active'] = update_data.is_active
            if update_data.metadata is not None:
                update_dict['metadata'] = update_data.metadata
            
            if not update_dict:
                return None
            
            response = self.supabase.table('chat_memories').update(update_dict).eq('id', str(memory_id)).execute()
            
            if response.data:
                memory_data = response.data[0]
                return ChatMemory(
                    id=UUID(memory_data['id']),
                    session_id=UUID(memory_data['session_id']),
                    memory_type=MemoryType(memory_data['memory_type']),
                    content=memory_data['content'],
                    importance_score=memory_data.get('importance_score', 0.5),
                    created_at=datetime.fromisoformat(memory_data['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(memory_data['updated_at'].replace('Z', '+00:00')),
                    is_active=memory_data.get('is_active', True),
                    metadata=memory_data.get('metadata', {})
                )
            return None
            
        except Exception as e:
            logger.error(f"更新聊天记忆失败: {e}")
            raise
    
    # 复合操作
    async def get_session_context(self, session_id: UUID, limit_messages: int = 20) -> ChatContextResponse:
        """获取会话的完整上下文（包括消息、RAG上下文和记忆）"""
        try:
            # 使用数据库函数获取上下文
            response = self.supabase.rpc('get_session_context', {
                'session_uuid': str(session_id),
                'limit_messages': limit_messages
            }).execute()
            
            messages = []
            memories = []
            total_tokens = 0
            
            for row in response.data or []:
                # 处理消息
                message = ChatMessageWithContext(
                    id=UUID(row['message_id']),
                    session_id=session_id,
                    role=MessageRole(row['role']),
                    content=row['content'],
                    created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
                    metadata={},
                    parent_message_id=None
                )
                
                # 处理RAG上下文
                if row.get('rag_context'):
                    # 这里需要根据实际的数据结构来处理
                    pass
                
                messages.append(message)
                
                # 处理记忆
                if row.get('memories'):
                    for memory_data in row['memories']:
                        memories.append(ChatMemory(
                            id=UUID(),  # 临时ID
                            session_id=session_id,
                            memory_type=MemoryType(memory_data['type']),
                            content=memory_data['content'],
                            importance_score=memory_data['importance'],
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            is_active=True,
                            metadata={}
                        ))
            
            return ChatContextResponse(
                session_id=session_id,
                messages=messages,
                memories=memories,
                total_tokens=total_tokens
            )
            
        except Exception as e:
            logger.error(f"获取会话上下文失败: {e}")
            raise
