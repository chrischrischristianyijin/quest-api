-- 创建聊天存储相关的表
-- 支持用户对话、RAG上下文和ChatGPT记忆功能

-- 1. 聊天会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(255), -- 会话标题，可以自动生成
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}' -- 存储额外信息，如模型配置等
);

-- 2. 聊天消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}', -- 存储消息元数据，如token数量、模型信息等
    parent_message_id UUID REFERENCES chat_messages(id) -- 支持消息树结构
);

-- 3. RAG上下文表
CREATE TABLE IF NOT EXISTS chat_rag_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    rag_chunks JSONB NOT NULL, -- 存储RAG检索到的分块信息
    context_text TEXT, -- 格式化后的上下文文本
    total_context_tokens INTEGER DEFAULT 0,
    extracted_keywords TEXT, -- 提取的关键词
    rag_k INTEGER DEFAULT 10,
    rag_min_score REAL DEFAULT 0.25,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. ChatGPT记忆表（支持ChatGPT的记忆功能）
CREATE TABLE IF NOT EXISTS chat_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL CHECK (memory_type IN ('user_preference', 'fact', 'context', 'insight')),
    content TEXT NOT NULL,
    importance_score REAL DEFAULT 0.5 CHECK (importance_score >= 0 AND importance_score <= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'
);

-- 5. 创建索引
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_rag_contexts_message_id ON chat_rag_contexts(message_id);
CREATE INDEX IF NOT EXISTS idx_chat_memories_session_id ON chat_memories(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_memories_type ON chat_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_chat_memories_importance ON chat_memories(importance_score DESC);

-- 6. 创建触发器自动更新updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_chat_sessions_updated_at 
    BEFORE UPDATE ON chat_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_memories_updated_at 
    BEFORE UPDATE ON chat_memories 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 7. 添加注释
COMMENT ON TABLE chat_sessions IS '聊天会话表，存储用户的对话会话';
COMMENT ON TABLE chat_messages IS '聊天消息表，存储会话中的所有消息';
COMMENT ON TABLE chat_rag_contexts IS 'RAG上下文表，存储每次对话的RAG检索上下文';
COMMENT ON TABLE chat_memories IS 'ChatGPT记忆表，存储AI助手的长期记忆';

-- 8. 创建视图：会话概览
CREATE OR REPLACE VIEW chat_session_overview AS
SELECT 
    cs.id,
    cs.user_id,
    cs.title,
    cs.created_at,
    cs.updated_at,
    cs.is_active,
    COUNT(cm.id) as message_count,
    MAX(cm.created_at) as last_message_at
FROM chat_sessions cs
LEFT JOIN chat_messages cm ON cs.id = cm.session_id
GROUP BY cs.id, cs.user_id, cs.title, cs.created_at, cs.updated_at, cs.is_active;

-- 9. 创建函数：获取会话的完整上下文
CREATE OR REPLACE FUNCTION get_session_context(session_uuid UUID, limit_messages INTEGER DEFAULT 20)
RETURNS TABLE(
    message_id UUID,
    role VARCHAR(20),
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    rag_context JSONB,
    memories JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cm.id as message_id,
        cm.role,
        cm.content,
        cm.created_at,
        crc.rag_chunks as rag_context,
        COALESCE(
            (SELECT jsonb_agg(
                jsonb_build_object(
                    'type', memory_type,
                    'content', content,
                    'importance', importance_score
                )
            ) FROM chat_memories 
            WHERE session_id = session_uuid 
            AND is_active = TRUE 
            ORDER BY importance_score DESC 
            LIMIT 5), 
            '[]'::jsonb
        ) as memories
    FROM chat_messages cm
    LEFT JOIN chat_rag_contexts crc ON cm.id = crc.message_id
    WHERE cm.session_id = session_uuid
    ORDER BY cm.created_at DESC
    LIMIT limit_messages;
END;
$$ LANGUAGE plpgsql;
