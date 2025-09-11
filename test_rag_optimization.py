#!/usr/bin/env python3
"""
测试RAG检索优化功能
"""

import os
import sys
import asyncio
sys.path.append('.')

from app.services.rag_service import RAGService
from app.core.database import get_supabase_service

async def test_rag_optimization():
    """测试RAG检索优化"""
    print("🚀 测试RAG检索优化功能...")
    
    try:
        # 初始化服务
        rag_service = RAGService()
        supabase = get_supabase_service()
        
        # 测试用户ID（需要替换为实际用户ID）
        test_user_id = "test-user-123"
        
        print(f"\n1. 测试用户 {test_user_id} 的insights数量...")
        
        # 查询用户insights
        insights_response = supabase.table('insights').select(
            'id, title, description, created_at'
        ).eq('user_id', test_user_id).execute()
        
        if insights_response.data:
            print(f"   ✅ 用户有 {len(insights_response.data)} 个insights")
            for insight in insights_response.data[:3]:  # 显示前3个
                print(f"   - {insight['title']} (ID: {insight['id']})")
        else:
            print("   ⚠️ 用户没有insights，将测试空结果处理")
        
        print(f"\n2. 测试用户insights的chunks数量...")
        
        # 查询用户chunks
        if insights_response.data:
            insight_ids = [insight['id'] for insight in insights_response.data]
            chunks_response = supabase.table('insight_chunks').select(
                'id, insight_id, chunk_index, chunk_text, embedding'
            ).in_('insight_id', insight_ids).not_.is_('embedding', 'null').execute()
            
            if chunks_response.data:
                print(f"   ✅ 找到 {len(chunks_response.data)} 个有embedding的chunks")
                
                # 统计每个insight的chunks数量
                insight_chunk_counts = {}
                for chunk in chunks_response.data:
                    insight_id = chunk['insight_id']
                    insight_chunk_counts[insight_id] = insight_chunk_counts.get(insight_id, 0) + 1
                
                print(f"   📊 每个insight的chunks分布:")
                for insight_id, count in list(insight_chunk_counts.items())[:5]:
                    print(f"      - {insight_id}: {count} chunks")
            else:
                print("   ⚠️ 用户insights中没有有embedding的chunks")
        else:
            print("   ⚠️ 没有insights，跳过chunks查询")
        
        print(f"\n3. 测试RAG检索功能...")
        
        # 测试查询
        test_queries = [
            "什么是人工智能？",
            "机器学习的基本概念",
            "深度学习应用"
        ]
        
        for query in test_queries:
            print(f"\n   🔍 查询: {query}")
            try:
                # 测试RAG检索
                rag_context = await rag_service.retrieve(
                    query=query,
                    user_id=test_user_id,
                    k=6,
                    min_score=0.2
                )
                
                print(f"   ✅ 检索到 {len(rag_context.chunks)} 个相关chunks")
                print(f"   📝 上下文长度: {rag_context.total_tokens} tokens")
                
                if rag_context.chunks:
                    print(f"   🎯 相似度范围: {min(c.score for c in rag_context.chunks):.3f} - {max(c.score for c in rag_context.chunks):.3f}")
                    print(f"   📚 来源insights: {len(set(c.insight_id for c in rag_context.chunks))} 个")
                else:
                    print("   ⚠️ 没有找到相关chunks")
                    
            except Exception as e:
                print(f"   ❌ 检索失败: {e}")
        
        print(f"\n4. 测试检索策略...")
        
        # 测试不同参数
        test_params = [
            {"k": 3, "min_score": 0.3, "desc": "高阈值，少量结果"},
            {"k": 10, "min_score": 0.1, "desc": "低阈值，多结果"},
            {"k": 6, "min_score": 0.2, "desc": "默认参数"}
        ]
        
        for params in test_params:
            print(f"\n   🧪 {params['desc']} (k={params['k']}, min_score={params['min_score']})")
            try:
                rag_context = await rag_service.retrieve(
                    query="测试查询",
                    user_id=test_user_id,
                    k=params['k'],
                    min_score=params['min_score']
                )
                print(f"   ✅ 检索到 {len(rag_context.chunks)} 个chunks")
            except Exception as e:
                print(f"   ❌ 失败: {e}")
        
        print(f"\n✅ RAG检索优化测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rag_optimization())
