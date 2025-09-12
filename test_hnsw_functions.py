#!/usr/bin/env python3
"""
测试Supabase中可用的HNSW搜索函数
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_supabase_service

async def test_hnsw_functions():
    """测试可用的HNSW搜索函数"""
    print("🧪 测试Supabase中的HNSW搜索函数...")
    
    supabase = get_supabase_service()
    
    # 测试常见的向量搜索函数
    test_functions = [
        'search_similar_chunks',
        'search_similar_chunks_by_text', 
        'search_chunks_by_embedding',
        'match_chunks',
        'vector_search',
        'similarity_search',
        'hnsw_search',
        'pgvector_search'
    ]
    
    for func_name in test_functions:
        try:
            print(f"\n📝 测试函数: {func_name}")
            
            # 尝试调用函数（使用最小参数）
            response = supabase.rpc(func_name, {
                'query_embedding': '[0.1, 0.2, 0.3]',
                'user_id_param': 'test_user',
                'limit_count': 5
            }).execute()
            
            print(f"   ✅ 函数 {func_name} 可用")
            print(f"   响应: {response.data[:2] if response.data else 'No data'}")
            
        except Exception as e:
            error_msg = str(e)
            if "Could not find the function" in error_msg:
                print(f"   ❌ 函数 {func_name} 不存在")
            elif "permission denied" in error_msg.lower():
                print(f"   ⚠️ 函数 {func_name} 存在但权限不足")
            else:
                print(f"   ⚠️ 函数 {func_name} 调用失败: {error_msg[:100]}...")
    
    # 测试原生SQL查询
    print(f"\n📝 测试原生SQL查询...")
    try:
        # 测试简单的向量查询
        test_sql = """
        SELECT id, insight_id, chunk_index, chunk_text
        FROM insight_chunks 
        WHERE embedding IS NOT NULL 
        LIMIT 1
        """
        
        response = supabase.rpc('execute_sql', {'sql': test_sql}).execute()
        print(f"   ✅ 原生SQL查询可用")
        print(f"   响应: {response.data[:1] if response.data else 'No data'}")
        
    except Exception as e:
        print(f"   ❌ 原生SQL查询失败: {e}")
        
        # 尝试其他可能的SQL执行函数
        for sql_func in ['sql', 'query', 'execute']:
            try:
                response = supabase.rpc(sql_func, {'query': test_sql}).execute()
                print(f"   ✅ 使用 {sql_func} 执行SQL成功")
                break
            except Exception:
                continue

async def test_vector_operations():
    """测试向量操作符"""
    print(f"\n🧪 测试PostgreSQL向量操作符...")
    
    supabase = get_supabase_service()
    
    # 测试向量操作符查询
    test_queries = [
        {
            'name': '测试 <=> 距离操作符',
            'sql': """
            SELECT id, embedding <=> '[0.1, 0.2, 0.3]'::vector as distance
            FROM insight_chunks 
            WHERE embedding IS NOT NULL 
            LIMIT 1
            """
        },
        {
            'name': '测试 <-> 余弦距离操作符', 
            'sql': """
            SELECT id, embedding <-> '[0.1, 0.2, 0.3]'::vector as cosine_distance
            FROM insight_chunks 
            WHERE embedding IS NOT NULL 
            LIMIT 1
            """
        }
    ]
    
    for test in test_queries:
        try:
            print(f"\n📝 {test['name']}")
            response = supabase.rpc('execute_sql', {'sql': test['sql']}).execute()
            print(f"   ✅ 成功: {response.data[:1] if response.data else 'No data'}")
        except Exception as e:
            print(f"   ❌ 失败: {e}")

async def main():
    """主测试函数"""
    print("🚀 开始测试Supabase HNSW功能...")
    print("=" * 60)
    
    await test_hnsw_functions()
    await test_vector_operations()
    
    print("\n🎉 测试完成!")
    print("\n📋 建议:")
    print("1. 根据测试结果选择可用的HNSW搜索方法")
    print("2. 如果原生SQL可用，直接使用向量操作符")
    print("3. 如果RPC函数可用，使用相应的搜索函数")

if __name__ == "__main__":
    asyncio.run(main())
