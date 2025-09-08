"""
Insight Chunks API 路由
用于查询和管理 insight 的文本分块数据
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.database import get_supabase_service
from app.models.insight_chunk import InsightChunkSummary, InsightChunksResponse, create_chunks_response
from app.services.auth_service import get_current_user_id
from app.services.embedding_service import get_embedding_service, is_embedding_enabled
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/insight-chunks", tags=["insight-chunks"])


@router.get("/{insight_id}", response_model=InsightChunksResponse)
async def get_insight_chunks(
    insight_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    limit: Optional[int] = Query(None, ge=1, le=100, description="限制返回的分块数量"),
    offset: Optional[int] = Query(0, ge=0, description="偏移量")
):
    """
    获取指定 insight 的分块数据
    
    Args:
        insight_id: insight ID
        current_user_id: 当前用户 ID
        limit: 限制返回的分块数量
        offset: 偏移量
    
    Returns:
        InsightChunksResponse: 分块数据列表
    """
    try:
        # 验证 insight 是否属于当前用户
        supabase_service = get_supabase_service()
        
        # 检查 insight 是否存在且属于该用户
        insight_check = (
            supabase_service
            .table('insights')
            .select('id')
            .eq('id', str(insight_id))
            .eq('user_id', str(current_user_id))
            .execute()
        )
        
        if hasattr(insight_check, 'error') and insight_check.error:
            logger.error(f"检查 insight 失败: {insight_check.error}")
            raise HTTPException(status_code=500, detail="检查 insight 失败")
        
        if not insight_check.data:
            raise HTTPException(status_code=404, detail="Insight 不存在或无权限访问")
        
        # 查询分块数据
        query = (
            supabase_service
            .table('insight_chunks')
            .select('*')
            .eq('insight_id', str(insight_id))
            .order('chunk_index', desc=False)
        )
        
        if limit is not None:
            query = query.limit(limit)
        
        if offset > 0:
            query = query.range(offset, offset + (limit or 100) - 1)
        
        result = query.execute()
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"查询分块数据失败: {result.error}")
            raise HTTPException(status_code=500, detail="查询分块数据失败")
        
        chunks_data = result.data or []
        
        # 转换为响应模型
        response = create_chunks_response(chunks_data)
        
        logger.info(f"用户 {current_user_id} 查询 insight {insight_id} 的分块数据，返回 {len(chunks_data)} 个分块")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分块数据异常: {e}")
        raise HTTPException(status_code=500, detail="获取分块数据失败")


@router.get("/{insight_id}/summary")
async def get_insight_chunks_summary(
    insight_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    获取指定 insight 的分块摘要信息
    
    Args:
        insight_id: insight ID
        current_user_id: 当前用户 ID
    
    Returns:
        dict: 分块摘要信息
    """
    try:
        # 验证 insight 是否属于当前用户
        supabase_service = get_supabase_service()
        
        # 检查 insight 是否存在且属于该用户
        insight_check = (
            supabase_service
            .table('insights')
            .select('id')
            .eq('id', str(insight_id))
            .eq('user_id', str(current_user_id))
            .execute()
        )
        
        if hasattr(insight_check, 'error') and insight_check.error:
            logger.error(f"检查 insight 失败: {insight_check.error}")
            raise HTTPException(status_code=500, detail="检查 insight 失败")
        
        if not insight_check.data:
            raise HTTPException(status_code=404, detail="Insight 不存在或无权限访问")
        
        # 查询分块统计信息
        result = (
            supabase_service
            .table('insight_chunks')
            .select('chunk_size, estimated_tokens, chunk_method')
            .eq('insight_id', str(insight_id))
            .execute()
        )
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"查询分块统计失败: {result.error}")
            raise HTTPException(status_code=500, detail="查询分块统计失败")
        
        chunks_data = result.data or []
        
        if not chunks_data:
            return {
                "total_chunks": 0,
                "total_size": 0,
                "total_tokens": 0,
                "avg_chunk_size": 0.0,
                "chunk_method": "unknown",
                "has_chunks": False
            }
        
        # 计算统计信息
        total_chunks = len(chunks_data)
        total_size = sum(chunk.get('chunk_size', 0) for chunk in chunks_data)
        total_tokens = sum(chunk.get('estimated_tokens', 0) for chunk in chunks_data if chunk.get('estimated_tokens'))
        avg_chunk_size = total_size / total_chunks if total_chunks > 0 else 0.0
        chunk_method = chunks_data[0].get('chunk_method', 'unknown') if chunks_data else 'unknown'
        
        summary = {
            "total_chunks": total_chunks,
            "total_size": total_size,
            "total_tokens": total_tokens,
            "avg_chunk_size": round(avg_chunk_size, 2),
            "chunk_method": chunk_method,
            "has_chunks": True
        }
        
        logger.info(f"用户 {current_user_id} 查询 insight {insight_id} 的分块摘要")
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分块摘要异常: {e}")
        raise HTTPException(status_code=500, detail="获取分块摘要失败")


@router.get("/{insight_id}/{chunk_index}")
async def get_insight_chunk_detail(
    insight_id: UUID,
    chunk_index: int,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    获取指定 insight 的特定分块详细内容
    
    Args:
        insight_id: insight ID
        chunk_index: 分块索引
        current_user_id: 当前用户 ID
    
    Returns:
        dict: 分块详细内容
    """
    try:
        # 验证 insight 是否属于当前用户
        supabase_service = get_supabase_service()
        
        # 检查 insight 是否存在且属于该用户
        insight_check = (
            supabase_service
            .table('insights')
            .select('id')
            .eq('id', str(insight_id))
            .eq('user_id', str(current_user_id))
            .execute()
        )
        
        if hasattr(insight_check, 'error') and insight_check.error:
            logger.error(f"检查 insight 失败: {insight_check.error}")
            raise HTTPException(status_code=500, detail="检查 insight 失败")
        
        if not insight_check.data:
            raise HTTPException(status_code=404, detail="Insight 不存在或无权限访问")
        
        # 查询特定分块
        result = (
            supabase_service
            .table('insight_chunks')
            .select('*')
            .eq('insight_id', str(insight_id))
            .eq('chunk_index', chunk_index)
            .execute()
        )
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"查询分块详情失败: {result.error}")
            raise HTTPException(status_code=500, detail="查询分块详情失败")
        
        chunk_data = result.data[0] if result.data else None
        
        if not chunk_data:
            raise HTTPException(status_code=404, detail="分块不存在")
        
        logger.info(f"用户 {current_user_id} 查询 insight {insight_id} 的分块 {chunk_index}")
        
        return chunk_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分块详情异常: {e}")
        raise HTTPException(status_code=500, detail="获取分块详情失败")


@router.get("/{insight_id}/similar")
async def find_similar_chunks(
    insight_id: UUID,
    chunk_index: int = Query(..., ge=0, description="参考分块索引"),
    similarity_threshold: float = Query(0.7, ge=0.0, le=1.0, description="相似度阈值"),
    max_results: int = Query(10, ge=1, le=50, description="最大返回结果数"),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    查找与指定分块相似的其他分块
    
    Args:
        insight_id: insight ID
        chunk_index: 参考分块索引
        similarity_threshold: 相似度阈值 (0.0-1.0)
        max_results: 最大返回结果数
        current_user_id: 当前用户 ID
    
    Returns:
        List[Dict]: 相似分块列表
    """
    try:
        if not is_embedding_enabled():
            raise HTTPException(status_code=400, detail="Embedding 功能未启用")
        
        # 验证 insight 是否属于当前用户
        supabase_service = get_supabase_service()
        
        # 检查 insight 是否存在且属于该用户
        insight_check = (
            supabase_service
            .table('insights')
            .select('id')
            .eq('id', str(insight_id))
            .eq('user_id', str(current_user_id))
            .execute()
        )
        
        if hasattr(insight_check, 'error') and insight_check.error:
            logger.error(f"检查 insight 失败: {insight_check.error}")
            raise HTTPException(status_code=500, detail="检查 insight 失败")
        
        if not insight_check.data:
            raise HTTPException(status_code=404, detail="Insight 不存在或无权限访问")
        
        # 获取参考分块
        reference_chunk = (
            supabase_service
            .table('insight_chunks')
            .select('id, embedding')
            .eq('insight_id', str(insight_id))
            .eq('chunk_index', chunk_index)
            .execute()
        )
        
        if hasattr(reference_chunk, 'error') and reference_chunk.error:
            logger.error(f"查询参考分块失败: {reference_chunk.error}")
            raise HTTPException(status_code=500, detail="查询参考分块失败")
        
        if not reference_chunk.data:
            raise HTTPException(status_code=404, detail="参考分块不存在")
        
        ref_chunk_data = reference_chunk.data[0]
        if not ref_chunk_data.get('embedding'):
            raise HTTPException(status_code=400, detail="参考分块没有 embedding 数据")
        
        # 使用数据库函数查找相似分块
        similar_chunks = (
            supabase_service
            .rpc('find_similar_chunks', {
                'target_chunk_id': ref_chunk_data['id'],
                'similarity_threshold': similarity_threshold,
                'max_results': max_results
            })
            .execute()
        )
        
        if hasattr(similar_chunks, 'error') and similar_chunks.error:
            logger.error(f"查询相似分块失败: {similar_chunks.error}")
            raise HTTPException(status_code=500, detail="查询相似分块失败")
        
        results = similar_chunks.data or []
        
        logger.info(f"用户 {current_user_id} 查询 insight {insight_id} 分块 {chunk_index} 的相似分块，返回 {len(results)} 个结果")
        
        return {
            "reference_chunk_id": ref_chunk_data['id'],
            "reference_chunk_index": chunk_index,
            "similarity_threshold": similarity_threshold,
            "similar_chunks": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查找相似分块异常: {e}")
        raise HTTPException(status_code=500, detail="查找相似分块失败")


@router.post("/search")
async def search_chunks_by_text(
    query_text: str,
    similarity_threshold: float = Query(0.7, ge=0.0, le=1.0, description="相似度阈值"),
    max_results: int = Query(10, ge=1, le=50, description="最大返回结果数"),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    基于文本搜索相似分块
    
    Args:
        query_text: 搜索文本
        similarity_threshold: 相似度阈值 (0.0-1.0)
        max_results: 最大返回结果数
        current_user_id: 当前用户 ID
    
    Returns:
        List[Dict]: 相似分块列表
    """
    try:
        if not is_embedding_enabled():
            raise HTTPException(status_code=400, detail="Embedding 功能未启用")
        
        if not query_text or not query_text.strip():
            raise HTTPException(status_code=400, detail="搜索文本不能为空")
        
        # 生成搜索文本的 embedding
        embedding_service = get_embedding_service()
        search_embedding = await embedding_service.generate_single_embedding(query_text)
        
        if not search_embedding:
            raise HTTPException(status_code=500, detail="生成搜索 embedding 失败")
        
        # 获取用户的所有分块（带 embedding）
        supabase_service = get_supabase_service()
        
        # 获取用户的所有 insight
        user_insights = (
            supabase_service
            .table('insights')
            .select('id')
            .eq('user_id', str(current_user_id))
            .execute()
        )
        
        if hasattr(user_insights, 'error') and user_insights.error:
            logger.error(f"查询用户 insights 失败: {user_insights.error}")
            raise HTTPException(status_code=500, detail="查询用户 insights 失败")
        
        insight_ids = [insight['id'] for insight in user_insights.data or []]
        
        if not insight_ids:
            return {
                "query_text": query_text,
                "similarity_threshold": similarity_threshold,
                "similar_chunks": []
            }
        
        # 查询所有有 embedding 的分块
        all_chunks = (
            supabase_service
            .table('insight_chunks')
            .select('id, insight_id, chunk_index, chunk_text, embedding, chunk_size')
            .in_('insight_id', insight_ids)
            .not_.is_('embedding', 'null')
            .execute()
        )
        
        if hasattr(all_chunks, 'error') and all_chunks.error:
            logger.error(f"查询分块失败: {all_chunks.error}")
            raise HTTPException(status_code=500, detail="查询分块失败")
        
        chunks_data = all_chunks.data or []
        
        # 计算相似度并排序
        similar_chunks = []
        for chunk in chunks_data:
            similarity = embedding_service.calculate_similarity(
                search_embedding['embedding'],
                chunk['embedding']
            )
            
            if similarity >= similarity_threshold:
                similar_chunks.append({
                    'chunk_id': chunk['id'],
                    'insight_id': chunk['insight_id'],
                    'chunk_index': chunk['chunk_index'],
                    'chunk_text': chunk['chunk_text'],
                    'chunk_size': chunk['chunk_size'],
                    'similarity': round(similarity, 4)
                })
        
        # 按相似度排序
        similar_chunks.sort(key=lambda x: x['similarity'], reverse=True)
        
        # 限制结果数量
        similar_chunks = similar_chunks[:max_results]
        
        logger.info(f"用户 {current_user_id} 搜索文本 '{query_text[:50]}...'，返回 {len(similar_chunks)} 个相似分块")
        
        return {
            "query_text": query_text,
            "similarity_threshold": similarity_threshold,
            "total_chunks_searched": len(chunks_data),
            "similar_chunks": similar_chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文本搜索异常: {e}")
        raise HTTPException(status_code=500, detail="文本搜索失败")
