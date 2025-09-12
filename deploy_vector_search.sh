#!/bin/bash

# 部署向量搜索函数到Supabase
echo "🚀 部署向量搜索函数到Supabase..."

# 检查环境变量
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "❌ 错误: 请设置 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY 环境变量"
    exit 1
fi

# 使用psql直接连接执行修复脚本
echo "🔧 执行函数修复脚本..."
psql "$SUPABASE_URL" -f database/migrations/fix_vector_search_function.sql

# 如果上面失败，尝试执行原始脚本
if [ $? -ne 0 ]; then
    echo "⚠️ 修复脚本失败，尝试执行原始脚本..."
    psql "$SUPABASE_URL" -f database/migrations/create_vector_search_function.sql
fi

echo "✅ 向量搜索函数部署完成!"
echo ""
echo "📋 使用方法:"
echo "1. 确保数据库中有insight_chunks表和insights表"
echo "2. 确保insight_chunks表有embedding列（vector(1536)类型）"
echo "3. 确保有HNSW索引"
echo "4. 测试函数: SELECT * FROM search_similar_chunks_by_vector('[0.1,0.2,...]'::vector(1536), 'user-uuid', 0.7, 10);"
