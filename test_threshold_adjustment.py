#!/usr/bin/env python3
"""
测试调整后的相似度阈值
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.rag_service import RAGService

async def test_threshold_adjustment():
    """测试调整后的相似度阈值"""
    print("🎯 测试调整后的相似度阈值 (0.25)")
    print("=" * 50)
    
    # 检查环境变量
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
        return
    
    rag_service = RAGService()
    
    # 测试用例
    test_query = "Python性能优化技巧"
    test_user_id = "test_user_123"
    
    print(f"📝 测试问题: {test_query}")
    print(f"👤 测试用户: {test_user_id}")
    print(f"🎯 相似度阈值: 0.25 (25%)")
    print("-" * 30)
    
    try:
        # 测试完整的RAG检索
        print("🚀 开始RAG检索测试...")
        rag_context = await rag_service.retrieve(
            query=test_query,
            user_id=test_user_id,
            k=5,
            min_score=0.25  # 使用新的阈值
        )
        
        print(f"✅ RAG检索完成")
        print(f"📊 找到 {len(rag_context.chunks)} 个相关分块")
        print(f"📝 上下文长度: {rag_context.total_tokens} tokens")
        
        if rag_context.chunks:
            print(f"🎯 最高分: {rag_context.chunks[0].score:.3f}")
            print(f"📄 第一个分块: {rag_context.chunks[0].chunk_text[:100]}...")
            
            # 显示所有分块的分数
            print(f"\n📈 所有分块的相似度分数:")
            for i, chunk in enumerate(rag_context.chunks, 1):
                print(f"  {i}. 分数: {chunk.score:.3f} - {chunk.chunk_text[:50]}...")
        else:
            print("ℹ️ 没有找到相关分块（阈值0.25可能太严格）")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 测试完成!")
    print("\n💡 提示:")
    print("- 如果结果太少，可以降低阈值到0.2或0.15")
    print("- 如果结果不够精确，可以进一步提高阈值到0.3")

if __name__ == "__main__":
    asyncio.run(test_threshold_adjustment())
