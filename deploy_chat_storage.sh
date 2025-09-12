#!/bin/bash

# 部署聊天存储系统到Supabase
echo "🚀 部署聊天存储系统到Supabase..."

# 检查环境变量
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "❌ 错误: 请设置 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY 环境变量"
    exit 1
fi

# 使用psql直接连接执行SQL脚本
echo "📝 执行聊天存储表创建脚本..."
psql "$SUPABASE_URL" -f database/migrations/create_chat_storage_tables.sql

if [ $? -eq 0 ]; then
    echo "✅ 聊天存储系统部署完成!"
    echo ""
    echo "📋 已创建的表:"
    echo "- chat_sessions: 聊天会话表"
    echo "- chat_messages: 聊天消息表"
    echo "- chat_rag_contexts: RAG上下文表"
    echo "- chat_memories: ChatGPT记忆表"
    echo ""
    echo "📋 已创建的功能:"
    echo "- 自动更新updated_at字段的触发器"
    echo "- chat_session_overview视图"
    echo "- get_session_context函数"
    echo ""
    echo "🎯 使用方法:"
    echo "1. 在聊天API中传入session_id参数"
    echo "2. 系统会自动存储用户消息、AI响应和RAG上下文"
    echo "3. 自动提取和存储ChatGPT记忆"
    echo "4. 使用聊天会话管理API管理历史对话"
else
    echo "❌ 部署失败，请检查数据库连接和权限"
    exit 1
fi
