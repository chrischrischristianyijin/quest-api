"""
Insight Chunks API 路由
用于查询和管理 insight 的文本分块数据
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.database import get_supabase_service
from app.models.insight_chunk import InsightChunkSummary, InsightChunksResponse, create_chunks_response
from app.services.auth_service import AuthService
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.services.embedding_service import get_embedding_service, is_embedding_enabled
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/insight-chunks", tags=["insight-chunks"])

# 认证相关
security = HTTPBearer()
auth_service = AuthService()

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UUID:
    """获取当前用户 ID"""
    current_user = await auth_service.get_current_user(credentials.credentials)
    return UUID(current_user['id'])


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


@router.get("/search/advanced")
async def advanced_chunk_search(
    current_user_id: UUID = Depends(get_current_user_id),
    insight_id: Optional[UUID] = Query(None, description="指定insight ID"),
    min_chunk_size: Optional[int] = Query(None, ge=1, description="最小分块大小"),
    max_chunk_size: Optional[int] = Query(None, ge=1, description="最大分块大小"),
    min_tokens: Optional[int] = Query(None, ge=1, description="最小token数"),
    max_tokens: Optional[int] = Query(None, ge=1, description="最大token数"),
    has_embedding: Optional[bool] = Query(None, description="是否有embedding"),
    chunk_method: Optional[str] = Query(None, description="分块方法"),
    created_after: Optional[str] = Query(None, description="创建时间之后 (ISO格式)"),
    created_before: Optional[str] = Query(None, description="创建时间之前 (ISO格式)"),
    limit: int = Query(50, ge=1, le=200, description="限制返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    高级分块搜索 - 支持多种筛选条件
    
    Args:
        current_user_id: 当前用户 ID
        insight_id: 指定insight ID
        min_chunk_size: 最小分块大小
        max_chunk_size: 最大分块大小
        min_tokens: 最小token数
        max_tokens: 最大token数
        has_embedding: 是否有embedding
        chunk_method: 分块方法
        created_after: 创建时间之后
        created_before: 创建时间之前
        limit: 限制返回数量
        offset: 偏移量
    
    Returns:
        dict: 筛选后的分块列表
    """
    try:
        supabase_service = get_supabase_service()
        
        # 构建基础查询
        query = supabase_service.table('insight_chunks').select('*')
        
        # 权限过滤：只查询用户自己的insights的分块
        if insight_id:
            # 验证insight是否属于用户
            insight_check = (
                supabase_service
                .table('insights')
                .select('id')
                .eq('id', str(insight_id))
                .eq('user_id', str(current_user_id))
                .execute()
            )
            
            if not insight_check.data:
                raise HTTPException(status_code=404, detail="Insight不存在或无权限访问")
            
            query = query.eq('insight_id', str(insight_id))
        else:
            # 获取用户的所有insight IDs
            user_insights = (
                supabase_service
                .table('insights')
                .select('id')
                .eq('user_id', str(current_user_id))
                .execute()
            )
            
            if user_insights.data:
                insight_ids = [insight['id'] for insight in user_insights.data]
                query = query.in_('insight_id', insight_ids)
            else:
                return {
                    "total_chunks": 0,
                    "chunks": [],
                    "filters_applied": {}
                }
        
        # 应用筛选条件
        filters_applied = {}
        
        if min_chunk_size is not None:
            query = query.gte('chunk_size', min_chunk_size)
            filters_applied['min_chunk_size'] = min_chunk_size
        
        if max_chunk_size is not None:
            query = query.lte('chunk_size', max_chunk_size)
            filters_applied['max_chunk_size'] = max_chunk_size
        
        if min_tokens is not None:
            query = query.gte('estimated_tokens', min_tokens)
            filters_applied['min_tokens'] = min_tokens
        
        if max_tokens is not None:
            query = query.lte('estimated_tokens', max_tokens)
            filters_applied['max_tokens'] = max_tokens
        
        if has_embedding is not None:
            if has_embedding:
                query = query.not_.is_('embedding', 'null')
            else:
                query = query.is_('embedding', 'null')
            filters_applied['has_embedding'] = has_embedding
        
        if chunk_method:
            query = query.eq('chunk_method', chunk_method)
            filters_applied['chunk_method'] = chunk_method
        
        if created_after:
            query = query.gte('created_at', created_after)
            filters_applied['created_after'] = created_after
        
        if created_before:
            query = query.lte('created_at', created_before)
            filters_applied['created_before'] = created_before
        
        # 排序和分页
        query = query.order('created_at', desc=True)
        query = query.range(offset, offset + limit - 1)
        
        # 执行查询
        result = query.execute()
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"高级搜索失败: {result.error}")
            raise HTTPException(status_code=500, detail="高级搜索失败")
        
        chunks_data = result.data or []
        
        # 获取总数（用于分页）
        count_query = supabase_service.table('insight_chunks').select('id', count='exact')
        
        # 重新应用所有筛选条件（除了分页）
        if insight_id:
            count_query = count_query.eq('insight_id', str(insight_id))
        elif 'insight_ids' in locals():
            count_query = count_query.in_('insight_id', insight_ids)
        
        for key, value in filters_applied.items():
            if key == 'min_chunk_size':
                count_query = count_query.gte('chunk_size', value)
            elif key == 'max_chunk_size':
                count_query = count_query.lte('chunk_size', value)
            elif key == 'min_tokens':
                count_query = count_query.gte('estimated_tokens', value)
            elif key == 'max_tokens':
                count_query = count_query.lte('estimated_tokens', value)
            elif key == 'has_embedding':
                if value:
                    count_query = count_query.not_.is_('embedding', 'null')
                else:
                    count_query = count_query.is_('embedding', 'null')
            elif key == 'chunk_method':
                count_query = count_query.eq('chunk_method', value)
            elif key == 'created_after':
                count_query = count_query.gte('created_at', value)
            elif key == 'created_before':
                count_query = count_query.lte('created_at', value)
        
        count_result = count_query.execute()
        total_count = count_result.count if hasattr(count_result, 'count') else len(chunks_data)
        
        logger.info(f"用户 {current_user_id} 执行高级搜索，返回 {len(chunks_data)} 个分块")
        
        return {
            "total_chunks": total_count,
            "chunks": chunks_data,
            "filters_applied": filters_applied,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(chunks_data) < total_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"高级搜索异常: {e}")
        raise HTTPException(status_code=500, detail="高级搜索失败")


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


@router.get("/stats")
async def get_chunks_statistics(
    current_user_id: UUID = Depends(get_current_user_id),
    insight_id: Optional[UUID] = Query(None, description="指定insight ID")
):
    """
    获取分块数据统计信息
    
    Args:
        current_user_id: 当前用户 ID
        insight_id: 指定insight ID（可选）
    
    Returns:
        dict: 统计信息
    """
    try:
        supabase_service = get_supabase_service()
        
        # 构建基础查询
        query = supabase_service.table('insight_chunks').select('*')
        
        # 权限过滤
        if insight_id:
            # 验证insight是否属于用户
            insight_check = (
                supabase_service
                .table('insights')
                .select('id')
                .eq('id', str(insight_id))
                .eq('user_id', str(current_user_id))
                .execute()
            )
            
            if not insight_check.data:
                raise HTTPException(status_code=404, detail="Insight不存在或无权限访问")
            
            query = query.eq('insight_id', str(insight_id))
        else:
            # 获取用户的所有insight IDs
            user_insights = (
                supabase_service
                .table('insights')
                .select('id')
                .eq('user_id', str(current_user_id))
                .execute()
            )
            
            if user_insights.data:
                insight_ids = [insight['id'] for insight in user_insights.data]
                query = query.in_('insight_id', insight_ids)
            else:
                return {
                    "total_chunks": 0,
                    "total_size": 0,
                    "total_tokens": 0,
                    "avg_chunk_size": 0,
                    "avg_tokens": 0,
                    "chunks_with_embedding": 0,
                    "embedding_coverage": 0.0,
                    "chunk_methods": {},
                    "size_distribution": {},
                    "token_distribution": {}
                }
        
        # 执行查询
        result = query.execute()
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"获取统计信息失败: {result.error}")
            raise HTTPException(status_code=500, detail="获取统计信息失败")
        
        chunks_data = result.data or []
        
        if not chunks_data:
            return {
                "total_chunks": 0,
                "total_size": 0,
                "total_tokens": 0,
                "avg_chunk_size": 0,
                "avg_tokens": 0,
                "chunks_with_embedding": 0,
                "embedding_coverage": 0.0,
                "chunk_methods": {},
                "size_distribution": {},
                "token_distribution": {}
            }
        
        # 计算基础统计
        total_chunks = len(chunks_data)
        total_size = sum(chunk.get('chunk_size', 0) for chunk in chunks_data)
        total_tokens = sum(chunk.get('estimated_tokens', 0) for chunk in chunks_data if chunk.get('estimated_tokens'))
        chunks_with_embedding = sum(1 for chunk in chunks_data if chunk.get('embedding'))
        
        # 计算平均值
        avg_chunk_size = total_size / total_chunks if total_chunks > 0 else 0
        avg_tokens = total_tokens / total_chunks if total_chunks > 0 else 0
        embedding_coverage = chunks_with_embedding / total_chunks if total_chunks > 0 else 0
        
        # 分块方法统计
        chunk_methods = {}
        for chunk in chunks_data:
            method = chunk.get('chunk_method', 'unknown')
            chunk_methods[method] = chunk_methods.get(method, 0) + 1
        
        # 大小分布统计
        size_ranges = {
            "small (<500)": 0,
            "medium (500-1500)": 0,
            "large (1500-3000)": 0,
            "xlarge (>3000)": 0
        }
        
        for chunk in chunks_data:
            size = chunk.get('chunk_size', 0)
            if size < 500:
                size_ranges["small (<500)"] += 1
            elif size < 1500:
                size_ranges["medium (500-1500)"] += 1
            elif size < 3000:
                size_ranges["large (1500-3000)"] += 1
            else:
                size_ranges["xlarge (>3000)"] += 1
        
        # Token分布统计
        token_ranges = {
            "low (<200)": 0,
            "medium (200-500)": 0,
            "high (500-1000)": 0,
            "very_high (>1000)": 0
        }
        
        for chunk in chunks_data:
            tokens = chunk.get('estimated_tokens', 0)
            if tokens < 200:
                token_ranges["low (<200)"] += 1
            elif tokens < 500:
                token_ranges["medium (200-500)"] += 1
            elif tokens < 1000:
                token_ranges["high (500-1000)"] += 1
            else:
                token_ranges["very_high (>1000)"] += 1
        
        statistics = {
            "total_chunks": total_chunks,
            "total_size": total_size,
            "total_tokens": total_tokens,
            "avg_chunk_size": round(avg_chunk_size, 2),
            "avg_tokens": round(avg_tokens, 2),
            "chunks_with_embedding": chunks_with_embedding,
            "embedding_coverage": round(embedding_coverage * 100, 2),  # 百分比
            "chunk_methods": chunk_methods,
            "size_distribution": size_ranges,
            "token_distribution": token_ranges,
            "scope": "single_insight" if insight_id else "all_insights"
        }
        
        logger.info(f"用户 {current_user_id} 获取分块统计信息，总分块数: {total_chunks}")
        
        return statistics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取统计信息异常: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")
