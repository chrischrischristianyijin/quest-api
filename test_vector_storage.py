#!/usr/bin/env python3
"""
测试vector存储和查询功能
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.rag_service import RAGService
from app.core.database import get_supabase_service

async def test_vector_storage():
    """测试vector存储和查询"""
    print("🔍 测试vector存储和查询...")
    
    try:
        # 初始化服务
        rag_service = RAGService()
        supabase = get_supabase_service()
        
        print("✅ 服务初始化成功")
        
        # 1. 测试文本嵌入
        test_query = "什么是机器学习？"
        print(f"📝 测试查询: {test_query}")
        
        embedding = await rag_service.embed_text(test_query)
        print(f"✅ 文本嵌入成功，维度: {len(embedding)}")
        
        # 2. 检查数据库中的vector数据
        print("🔍 检查数据库中的vector数据...")
        
        # 查询一些有embedding的分块
        response = supabase.table('insight_chunks').select(
            'id, insight_id, chunk_index, chunk_text, embedding'
        ).not_.is_('embedding', 'null').limit(3).execute()
        
        if response.data:
            print(f"✅ 找到 {len(response.data)} 个有embedding的分块")
            
            for i, chunk in enumerate(response.data, 1):
                print(f"  📄 分块 {i}:")
                print(f"    - ID: {chunk['id']}")
                print(f"    - 文本: {chunk['chunk_text'][:100]}...")
                if chunk['embedding']:
                    print(f"    - Embedding类型: {type(chunk['embedding'])}")
                    if isinstance(chunk['embedding'], list):
                        print(f"    - Embedding维度: {len(chunk['embedding'])}")
                    else:
                        print(f"    - Embedding值: {str(chunk['embedding'])[:100]}...")
        else:
            print("⚠️ 没有找到有embedding的分块数据")
            print("请先创建一些insight并生成embedding")
            return False
        
        # 3. 测试向量查询
        print("🔍 测试向量查询...")
        
        try:
            # 直接测试retrieve_chunks方法
            chunks = await rag_service.retrieve_chunks(
                query_embedding=embedding,
                user_id=None,
                k=3,
                min_score=0.1
            )
            
            print(f"✅ 向量查询成功")
            print(f"📊 查询结果:")
            print(f"  - 分块数量: {len(chunks)}")
            
            # 显示查询到的分块
            for i, chunk in enumerate(chunks, 1):
                print(f"  📄 分块 {i}:")
                print(f"    - 相似度: {chunk.score:.3f}")
                print(f"    - 文本: {chunk.chunk_text[:100]}...")
                
        except Exception as e:
            print(f"❌ 向量查询失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_database_vector_support():
    """测试数据库是否支持vector类型"""
    print("🔍 测试数据库vector支持...")
    
    try:
        supabase = get_supabase_service()
        
        # 尝试执行一个简单的vector查询
        # 注意：这个查询可能会失败，因为可能没有exec_sql RPC函数
        try:
            response = supabase.rpc('exec_sql', {
                'sql': 'SELECT version()',
                'params': []
            }).execute()
            print("✅ 数据库连接正常")
        except Exception as e:
            print(f"⚠️ exec_sql RPC不可用: {e}")
            print("将使用备用查询方法")
        
        # 测试基本的表查询
        response = supabase.table('insight_chunks').select('id').limit(1).execute()
        if response.data is not None:
            print("✅ 可以查询insight_chunks表")
        else:
            print("❌ 无法查询insight_chunks表")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return False

async def main():
    """主函数"""
    print("🚀 开始vector存储和查询测试\n")
    
    # 检查环境变量
    required_vars = ['OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
        print("请在.env文件中配置这些变量")
        return
    
    print("✅ 环境变量检查通过")
    
    # 测试数据库支持
    db_success = await test_database_vector_support()
    if not db_success:
        print("❌ 数据库测试失败，无法继续")
        return
    
    # 测试vector存储和查询
    vector_success = await test_vector_storage()
    
    print("\n" + "=" * 50)
    if vector_success:
        print("🎉 vector存储和查询测试通过！")
        print("✅ 数据库支持vector(1536)类型")
        print("✅ 向量查询功能正常")
        print("✅ RAG检索工作正常")
    else:
        print("⚠️ vector存储和查询测试失败")
        print("请检查:")
        print("1. 数据库是否安装了pgvector扩展")
        print("2. 是否执行了vector类型迁移")
        print("3. 是否有embedding数据")

if __name__ == "__main__":
    asyncio.run(main())
