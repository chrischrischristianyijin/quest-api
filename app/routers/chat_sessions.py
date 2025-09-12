from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from uuid import UUID
import logging

from app.services.chat_storage_service import ChatStorageService
from app.models.chat_storage import (
    ChatSession, ChatSessionCreate, ChatSessionUpdate, ChatSessionOverview,
    ChatMessageWithContext, ChatContextResponse, ChatSessionListResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["聊天会话管理"])

# 依赖注入
def get_chat_storage_service() -> ChatStorageService:
    return ChatStorageService()

@router.post("/sessions", response_model=ChatSession)
async def create_chat_session(
    session_data: ChatSessionCreate,
    chat_storage: ChatStorageService = Depends(get_chat_storage_service)
):
    """创建新的聊天会话"""
    try:
        session = await chat_storage.create_session(session_data)
        logger.info(f"创建聊天会话: {session.id}")
        return session
    except Exception as e:
        logger.error(f"创建聊天会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建聊天会话失败"
        )

@router.get("/sessions", response_model=ChatSessionListResponse)
async def get_user_sessions(
    user_id: UUID,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="页大小"),
    chat_storage: ChatStorageService = Depends(get_chat_storage_service)
):
    """获取用户的聊天会话列表"""
    try:
        sessions = await chat_storage.get_user_sessions(user_id, page, size)
        
        # 获取总数（简化处理，实际应该单独查询）
        total = len(sessions)  # 这里应该查询总数
        
        return ChatSessionListResponse(
            sessions=sessions,
            total=total,
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"获取用户会话列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话列表失败"
        )

@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_chat_session(
    session_id: UUID,
    chat_storage: ChatStorageService = Depends(get_chat_storage_service)
):
    """获取聊天会话详情"""
    try:
        session = await chat_storage.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取聊天会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话失败"
        )

@router.put("/sessions/{session_id}", response_model=ChatSession)
async def update_chat_session(
    session_id: UUID,
    update_data: ChatSessionUpdate,
    chat_storage: ChatStorageService = Depends(get_chat_storage_service)
):
    """更新聊天会话"""
    try:
        session = await chat_storage.update_session(session_id, update_data)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        logger.info(f"更新聊天会话: {session_id}")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新聊天会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新会话失败"
        )

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageWithContext])
async def get_session_messages(
    session_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="消息数量限制"),
    chat_storage: ChatStorageService = Depends(get_chat_storage_service)
):
    """获取会话的消息列表"""
    try:
        messages = await chat_storage.get_session_messages(session_id, limit)
        return messages
    except Exception as e:
        logger.error(f"获取会话消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取消息失败"
        )

@router.get("/sessions/{session_id}/context", response_model=ChatContextResponse)
async def get_session_context(
    session_id: UUID,
    limit_messages: int = Query(20, ge=1, le=100, description="消息数量限制"),
    chat_storage: ChatStorageService = Depends(get_chat_storage_service)
):
    """获取会话的完整上下文（包括消息、RAG上下文和记忆）"""
    try:
        context = await chat_storage.get_session_context(session_id, limit_messages)
        return context
    except Exception as e:
        logger.error(f"获取会话上下文失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取上下文失败"
        )

@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: UUID,
    chat_storage: ChatStorageService = Depends(get_chat_storage_service)
):
    """删除聊天会话（软删除）"""
    try:
        update_data = ChatSessionUpdate(is_active=False)
        session = await chat_storage.update_session(session_id, update_data)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        logger.info(f"删除聊天会话: {session_id}")
        return {"message": "会话已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除聊天会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除会话失败"
        )
