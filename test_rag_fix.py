#!/usr/bin/env python3
"""
测试修复后的RAG功能
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.rag_service import RAGService

async def test_rag_retrieve():
    """测试RAG检索功能"""
    print("🔍 测试修复后的RAG检索功能")
    print("=" * 50)
    
    # 检查环境变量
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
        return
    
    rag_service = RAGService()
    
    # 测试用例
    test_query = "如何提高Python代码的性能？"
    test_user_id = "test_user_123"
    
    print(f"📝 测试问题: {test_query}")
    print(f"👤 测试用户: {test_user_id}")
    print("-" * 30)
    
    try:
        # 测试完整的RAG检索流程
        rag_context = await rag_service.retrieve(
            query=test_query,
            user_id=test_user_id,
            k=5,
            min_score=0.2
        )
        
        print(f"✅ RAG检索成功")
        print(f"📊 找到 {len(rag_context.chunks)} 个相关分块")
        print(f"📝 上下文长度: {rag_context.total_tokens} tokens")
        
        if rag_context.chunks:
            print(f"🎯 最高分: {rag_context.chunks[0].score:.3f}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n🎉 测试完成!")

if __name__ == "__main__":
    asyncio.run(test_rag_retrieve())
