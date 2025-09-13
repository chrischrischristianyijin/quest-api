#!/usr/bin/env python3
"""
测试增强后的RAG功能
验证insight标题、URL和summary是否正确返回给前端
"""

import asyncio
import json
import os
import sys
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import RAGService
from app.models.chat import RAGChunk

async def test_enhanced_rag():
    """测试增强后的RAG功能"""
    print("🧪 开始测试增强后的RAG功能...")
    
    try:
        # 初始化RAG服务
        rag_service = RAGService()
        
        # 测试查询
        test_query = "人工智能的发展趋势"
        test_user_id = "00000000-0000-0000-0000-000000000001"  # 替换为实际的用户ID
        
        print(f"📝 测试查询: {test_query}")
        print(f"👤 用户ID: {test_user_id}")
        
        # 执行RAG检索
        print("\n🔍 执行RAG检索...")
        rag_context = await rag_service.retrieve(
            query=test_query,
            user_id=test_user_id,
            k=5,
            min_score=0.25
        )
        
        print(f"✅ RAG检索完成，找到 {len(rag_context.chunks)} 个相关chunks")
        
        # 检查每个chunk的insight信息
        print("\n📊 检查chunk的insight信息:")
        for i, chunk in enumerate(rag_context.chunks, 1):
            print(f"\n--- Chunk {i} ---")
            print(f"ID: {chunk.id}")
            print(f"Insight ID: {chunk.insight_id}")
            print(f"相似度分数: {chunk.score:.3f}")
            print(f"标题: {chunk.insight_title or '无'}")
            print(f"URL: {chunk.insight_url or '无'}")
            print(f"摘要: {chunk.insight_summary[:100] + '...' if chunk.insight_summary and len(chunk.insight_summary) > 100 else chunk.insight_summary or '无'}")
            print(f"文本片段: {chunk.chunk_text[:200]}...")
        
        # 测试上下文格式化
        print("\n📝 测试上下文格式化...")
        formatted_context = rag_service.format_context(rag_context.chunks, max_tokens=2000)
        
        print(f"✅ 上下文格式化完成")
        print(f"总token数: {formatted_context.total_tokens}")
        print(f"包含chunks数: {len(formatted_context.chunks)}")
        
        # 显示格式化的上下文（前500字符）
        print(f"\n📄 格式化上下文预览:")
        print("=" * 50)
        print(formatted_context.context_text[:500] + "..." if len(formatted_context.context_text) > 500 else formatted_context.context_text)
        print("=" * 50)
        
        # 模拟前端接收的sources格式
        print("\n🎯 模拟前端接收的sources格式:")
        sources = [
            {
                "id": str(chunk.id),
                "insight_id": str(chunk.insight_id),
                "score": chunk.score,
                "index": chunk.chunk_index,
                "title": chunk.insight_title,
                "url": chunk.insight_url
            }
            for chunk in rag_context.chunks
        ]
        
        print(json.dumps(sources, indent=2, ensure_ascii=False))
        
        # 验证功能
        print("\n✅ 功能验证:")
        chunks_with_title = [chunk for chunk in rag_context.chunks if chunk.insight_title]
        chunks_with_url = [chunk for chunk in rag_context.chunks if chunk.insight_url]
        chunks_with_summary = [chunk for chunk in rag_context.chunks if chunk.insight_summary]
        
        print(f"- 包含标题的chunks: {len(chunks_with_title)}/{len(rag_context.chunks)}")
        print(f"- 包含URL的chunks: {len(chunks_with_url)}/{len(rag_context.chunks)}")
        print(f"- 包含摘要的chunks: {len(chunks_with_summary)}/{len(rag_context.chunks)}")
        
        if chunks_with_title:
            print("✅ 标题信息获取成功")
        else:
            print("⚠️  未获取到标题信息")
            
        if chunks_with_url:
            print("✅ URL信息获取成功")
        else:
            print("⚠️  未获取到URL信息")
            
        if chunks_with_summary:
            print("✅ 摘要信息获取成功")
        else:
            print("⚠️  未获取到摘要信息")
        
        print("\n🎉 测试完成!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

async def test_insight_info_fetch():
    """测试insight信息获取功能"""
    print("\n🔍 测试insight信息获取功能...")
    
    try:
        rag_service = RAGService()
        
        # 测试批量获取insight信息
        test_insight_ids = ["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"]
        
        insights_info = await rag_service._get_insights_info(test_insight_ids)
        
        print(f"获取到 {len(insights_info)} 个insight的信息:")
        for insight_id, info in insights_info.items():
            print(f"- {insight_id}: {info}")
        
    except Exception as e:
        print(f"❌ insight信息获取测试失败: {e}")

if __name__ == "__main__":
    print("🚀 启动增强RAG功能测试")
    print("=" * 50)
    
    # 运行测试
    asyncio.run(test_enhanced_rag())
    asyncio.run(test_insight_info_fetch())
    
    print("\n" + "=" * 50)
    print("🏁 所有测试完成")
