#!/usr/bin/env python3
"""
RAG服务测试脚本
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import RAGService

async def test_rag_service():
    """测试RAG服务"""
    print("🔍 测试RAG服务...")
    
    try:
        # 初始化服务
        rag_service = RAGService()
        print("✅ RAG服务初始化成功")
        
        # 测试文本嵌入
        test_query = "什么是人工智能？"
        print(f"📝 测试查询: {test_query}")
        
        embedding = await rag_service.embed_text(test_query)
        print(f"✅ 文本嵌入成功，维度: {len(embedding)}")
        
        # 测试检索
        print("🔍 开始检索相关分块...")
        rag_context = await rag_service.retrieve(
            query=test_query,
            user_id=None,  # 测试所有用户的数据
            k=3,
            min_score=0.1
        )
        
        print(f"✅ 检索完成")
        print(f"📊 检索结果:")
        print(f"  - 分块数量: {len(rag_context.chunks)}")
        print(f"  - 上下文长度: {rag_context.total_tokens} tokens")
        print(f"  - 上下文文本: {rag_context.context_text[:200]}...")
        
        # 显示分块详情
        for i, chunk in enumerate(rag_context.chunks, 1):
            print(f"  📄 分块 {i}:")
            print(f"    - ID: {chunk.id}")
            print(f"    - 相似度: {chunk.score:.3f}")
            print(f"    - 文本: {chunk.chunk_text[:100]}...")
            print(f"    - 大小: {chunk.chunk_size} 字符")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("🚀 开始RAG服务测试\n")
    
    # 检查环境变量
    required_vars = ['OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
        print("请在.env文件中配置这些变量")
        return
    
    print("✅ 环境变量检查通过")
    
    # 运行测试
    success = await test_rag_service()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 RAG服务测试通过！")
    else:
        print("⚠️ RAG服务测试失败，请检查配置和日志")

if __name__ == "__main__":
    asyncio.run(main())
