"""
Source合并工具
用于将来自同一个insight的多个chunks合并为一个source
"""

from typing import List, Dict, Any
from app.models.chat import RAGChunk

def merge_chunks_to_sources(chunks: List[RAGChunk]) -> List[Dict[str, Any]]:
    """
    将chunks按insight_id合并为sources
    
    Args:
        chunks: RAG检索到的chunks列表
    
    Returns:
        合并后的sources列表，每个insight只出现一次
    """
    if not chunks:
        return []
    
    # 按insight_id分组
    insight_groups = {}
    for chunk in chunks:
        insight_id = str(chunk.insight_id)
        
        if insight_id not in insight_groups:
            insight_groups[insight_id] = {
                'chunks': [],
                'insight_id': insight_id,
                'title': chunk.insight_title,
                'url': chunk.insight_url,
                'summary': chunk.insight_summary
            }
        
        insight_groups[insight_id]['chunks'].append(chunk)
    
    # 构建sources列表
    sources = []
    for insight_id, group in insight_groups.items():
        # 计算该insight的最高分数
        max_score = max(chunk.score for chunk in group['chunks'])
        
        # 获取所有chunk的索引
        chunk_indices = [chunk.chunk_index for chunk in group['chunks']]
        chunk_indices.sort()
        
        # 构建source信息
        source = {
            'insight_id': insight_id,
            'title': group['title'],
            'url': group['url'],
            'score': max_score,
            'chunk_count': len(group['chunks']),
            'chunk_indices': chunk_indices,
            'summary': group['summary']
        }
        
        sources.append(source)
    
    # 按分数排序（降序）
    sources.sort(key=lambda x: x['score'], reverse=True)
    
    return sources

def merge_chunks_to_sources_with_details(chunks: List[RAGChunk]) -> List[Dict[str, Any]]:
    """
    将chunks按insight_id合并为sources，包含详细信息
    
    Args:
        chunks: RAG检索到的chunks列表
    
    Returns:
        合并后的sources列表，包含每个chunk的详细信息
    """
    if not chunks:
        return []
    
    # 按insight_id分组
    insight_groups = {}
    for chunk in chunks:
        insight_id = str(chunk.insight_id)
        
        if insight_id not in insight_groups:
            insight_groups[insight_id] = {
                'chunks': [],
                'insight_id': insight_id,
                'title': chunk.insight_title,
                'url': chunk.insight_url,
                'summary': chunk.insight_summary
            }
        
        insight_groups[insight_id]['chunks'].append(chunk)
    
    # 构建sources列表
    sources = []
    for insight_id, group in insight_groups.items():
        # 按分数排序chunks
        sorted_chunks = sorted(group['chunks'], key=lambda x: x.score, reverse=True)
        
        # 计算统计信息
        max_score = sorted_chunks[0].score
        avg_score = sum(chunk.score for chunk in sorted_chunks) / len(sorted_chunks)
        chunk_indices = sorted([chunk.chunk_index for chunk in sorted_chunks])
        
        # 构建chunk详情
        chunk_details = []
        for chunk in sorted_chunks:
            chunk_details.append({
                'id': str(chunk.id),
                'chunk_index': chunk.chunk_index,
                'score': chunk.score,
                'text_preview': chunk.chunk_text[:200] + '...' if len(chunk.chunk_text) > 200 else chunk.chunk_text
            })
        
        # 构建source信息
        source = {
            'insight_id': insight_id,
            'title': group['title'],
            'url': group['url'],
            'summary': group['summary'],
            'max_score': max_score,
            'avg_score': round(avg_score, 3),
            'chunk_count': len(sorted_chunks),
            'chunk_indices': chunk_indices,
            'chunks': chunk_details
        }
        
        sources.append(source)
    
    # 按最高分数排序（降序）
    sources.sort(key=lambda x: x['max_score'], reverse=True)
    
    return sources
