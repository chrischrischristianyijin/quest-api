#!/usr/bin/env python3
"""
测试Source合并功能
验证多个chunks来自同一个insight时是否正确合并
"""

import sys
import os
from datetime import datetime
from uuid import UUID, uuid4

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.chat import RAGChunk
from app.utils.source_merger import merge_chunks_to_sources, merge_chunks_to_sources_with_details

def test_source_merger():
    """测试source合并功能"""
    print("🧪 开始测试Source合并功能...")
    
    # 创建测试数据
    insight_id_1 = uuid4()
    insight_id_2 = uuid4()
    
    # 创建测试chunks - 同一个insight有多个chunks
    test_chunks = [
        RAGChunk(
            id=uuid4(),
            insight_id=insight_id_1,
            chunk_index=0,
            chunk_text="人工智能是计算机科学的一个分支，它企图了解智能的实质...",
            chunk_size=100,
            score=0.85,
            created_at=datetime.now(),
            insight_title="人工智能发展趋势分析",
            insight_url="https://example.com/ai-trends",
            insight_summary="本文详细分析了人工智能技术的发展历程和未来趋势"
        ),
        RAGChunk(
            id=uuid4(),
            insight_id=insight_id_1,  # 同一个insight
            chunk_index=1,
            chunk_text="机器学习是人工智能的核心技术之一，通过算法让计算机...",
            chunk_size=95,
            score=0.78,
            created_at=datetime.now(),
            insight_title="人工智能发展趋势分析",
            insight_url="https://example.com/ai-trends",
            insight_summary="本文详细分析了人工智能技术的发展历程和未来趋势"
        ),
        RAGChunk(
            id=uuid4(),
            insight_id=insight_id_2,  # 不同的insight
            chunk_index=0,
            chunk_text="区块链技术是一种分布式账本技术，具有去中心化...",
            chunk_size=110,
            score=0.72,
            created_at=datetime.now(),
            insight_title="区块链技术应用",
            insight_url="https://example.com/blockchain",
            insight_summary="区块链技术在金融、供应链等领域的应用前景"
        ),
        RAGChunk(
            id=uuid4(),
            insight_id=insight_id_1,  # 又是第一个insight
            chunk_index=2,
            chunk_text="深度学习是机器学习的一个子领域，使用多层神经网络...",
            chunk_size=105,
            score=0.68,
            created_at=datetime.now(),
            insight_title="人工智能发展趋势分析",
            insight_url="https://example.com/ai-trends",
            insight_summary="本文详细分析了人工智能技术的发展历程和未来趋势"
        )
    ]
    
    print(f"📊 测试数据:")
    print(f"- 总共 {len(test_chunks)} 个chunks")
    print(f"- Insight 1 ({insight_id_1}): 3个chunks")
    print(f"- Insight 2 ({insight_id_2}): 1个chunk")
    
    # 测试基础合并功能
    print("\n🔍 测试基础合并功能...")
    merged_sources = merge_chunks_to_sources(test_chunks)
    
    print(f"✅ 合并后得到 {len(merged_sources)} 个sources:")
    for i, source in enumerate(merged_sources, 1):
        print(f"\n--- Source {i} ---")
        print(f"Insight ID: {source['insight_id']}")
        print(f"标题: {source['title']}")
        print(f"URL: {source['url']}")
        print(f"最高分数: {source['score']:.3f}")
        print(f"Chunk数量: {source['chunk_count']}")
        print(f"Chunk索引: {source['chunk_indices']}")
        print(f"摘要: {source['summary'][:100]}..." if source['summary'] else "摘要: 无")
    
    # 验证合并结果
    print("\n✅ 验证合并结果:")
    assert len(merged_sources) == 2, f"应该有2个sources，实际得到{len(merged_sources)}个"
    
    # 检查第一个insight的合并
    insight_1_source = next((s for s in merged_sources if s['insight_id'] == str(insight_id_1)), None)
    assert insight_1_source is not None, "找不到第一个insight的source"
    assert insight_1_source['chunk_count'] == 3, f"第一个insight应该有3个chunks，实际有{insight_1_source['chunk_count']}个"
    assert insight_1_source['score'] == 0.85, f"最高分数应该是0.85，实际是{insight_1_source['score']}"
    assert set(insight_1_source['chunk_indices']) == {0, 1, 2}, f"Chunk索引应该是[0,1,2]，实际是{insight_1_source['chunk_indices']}"
    
    # 检查第二个insight
    insight_2_source = next((s for s in merged_sources if s['insight_id'] == str(insight_id_2)), None)
    assert insight_2_source is not None, "找不到第二个insight的source"
    assert insight_2_source['chunk_count'] == 1, f"第二个insight应该有1个chunk，实际有{insight_2_source['chunk_count']}个"
    assert insight_2_source['score'] == 0.72, f"最高分数应该是0.72，实际是{insight_2_source['score']}"
    
    print("✅ 基础合并功能测试通过")
    
    # 测试详细合并功能
    print("\n🔍 测试详细合并功能...")
    detailed_sources = merge_chunks_to_sources_with_details(test_chunks)
    
    print(f"✅ 详细合并后得到 {len(detailed_sources)} 个sources:")
    for i, source in enumerate(detailed_sources, 1):
        print(f"\n--- Detailed Source {i} ---")
        print(f"Insight ID: {source['insight_id']}")
        print(f"标题: {source['title']}")
        print(f"最高分数: {source['max_score']:.3f}")
        print(f"平均分数: {source['avg_score']:.3f}")
        print(f"Chunk数量: {source['chunk_count']}")
        print(f"Chunks详情:")
        for j, chunk_detail in enumerate(source['chunks'], 1):
            print(f"  {j}. 索引{chunk_detail['chunk_index']}, 分数{chunk_detail['score']:.3f}")
            print(f"     预览: {chunk_detail['text_preview']}")
    
    # 验证详细合并结果
    print("\n✅ 验证详细合并结果:")
    assert len(detailed_sources) == 2, f"应该有2个详细sources，实际得到{len(detailed_sources)}个"
    
    # 检查第一个insight的详细合并
    insight_1_detailed = next((s for s in detailed_sources if s['insight_id'] == str(insight_id_1)), None)
    assert insight_1_detailed is not None, "找不到第一个insight的详细source"
    assert len(insight_1_detailed['chunks']) == 3, f"应该有3个chunk详情，实际有{len(insight_1_detailed['chunks'])}个"
    
    # 验证chunks按分数排序
    chunk_scores = [chunk['score'] for chunk in insight_1_detailed['chunks']]
    assert chunk_scores == sorted(chunk_scores, reverse=True), "Chunks应该按分数降序排列"
    
    print("✅ 详细合并功能测试通过")
    
    # 测试空列表
    print("\n🔍 测试边界情况...")
    empty_sources = merge_chunks_to_sources([])
    assert empty_sources == [], "空列表应该返回空列表"
    print("✅ 空列表测试通过")
    
    print("\n🎉 所有测试通过！")
    
    # 模拟前端接收的格式
    print("\n🎯 模拟前端接收的格式:")
    import json
    frontend_sources = [
        {
            "insight_id": source["insight_id"],
            "title": source["title"],
            "url": source["url"],
            "score": source["score"],
            "chunk_count": source["chunk_count"],
            "chunk_indices": source["chunk_indices"]
        }
        for source in merged_sources
    ]
    
    print(json.dumps(frontend_sources, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    print("🚀 启动Source合并功能测试")
    print("=" * 50)
    
    test_source_merger()
    
    print("\n" + "=" * 50)
    print("🏁 测试完成")
