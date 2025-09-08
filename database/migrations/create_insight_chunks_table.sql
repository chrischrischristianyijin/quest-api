-- 创建 insight_chunks 表
-- 用于存储文本分块数据

CREATE TABLE IF NOT EXISTS insight_chunks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    insight_id UUID NOT NULL REFERENCES insights(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL, -- 分块序号
    chunk_text TEXT NOT NULL, -- 分块文本内容
    chunk_size INTEGER NOT NULL, -- 分块大小（字符数）
    estimated_tokens INTEGER, -- 预估 token 数
    chunk_method VARCHAR(50) DEFAULT 'recursive', -- 分块方法
    chunk_overlap INTEGER DEFAULT 200, -- 重叠大小
    embedding REAL[], -- 文本向量表示
    embedding_model VARCHAR(100), -- 生成 embedding 的模型
    embedding_tokens INTEGER, -- 生成 embedding 消耗的 token 数
    embedding_generated_at TIMESTAMP WITH TIME ZONE, -- embedding 生成时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_insight_chunks_insight_id ON insight_chunks(insight_id);
CREATE INDEX IF NOT EXISTS idx_insight_chunks_chunk_index ON insight_chunks(insight_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_insight_chunks_created_at ON insight_chunks(created_at);
CREATE INDEX IF NOT EXISTS idx_insight_chunks_embedding_model ON insight_chunks(embedding_model);
CREATE INDEX IF NOT EXISTS idx_insight_chunks_embedding_generated_at ON insight_chunks(embedding_generated_at);

-- 创建唯一约束：每个 insight 的 chunk_index 必须唯一
CREATE UNIQUE INDEX IF NOT EXISTS idx_insight_chunks_unique 
ON insight_chunks(insight_id, chunk_index);

-- 添加 RLS (Row Level Security) 策略
ALTER TABLE insight_chunks ENABLE ROW LEVEL SECURITY;

-- 用户只能访问自己的 insight 的分块数据
CREATE POLICY "Users can view their own insight chunks" ON insight_chunks
    FOR SELECT USING (
        insight_id IN (
            SELECT id FROM insights WHERE user_id = auth.uid()
        )
    );

-- 用户只能插入自己 insight 的分块数据
CREATE POLICY "Users can insert their own insight chunks" ON insight_chunks
    FOR INSERT WITH CHECK (
        insight_id IN (
            SELECT id FROM insights WHERE user_id = auth.uid()
        )
    );

-- 用户只能更新自己 insight 的分块数据
CREATE POLICY "Users can update their own insight chunks" ON insight_chunks
    FOR UPDATE USING (
        insight_id IN (
            SELECT id FROM insights WHERE user_id = auth.uid()
        )
    );

-- 用户只能删除自己 insight 的分块数据
CREATE POLICY "Users can delete their own insight chunks" ON insight_chunks
    FOR DELETE USING (
        insight_id IN (
            SELECT id FROM insights WHERE user_id = auth.uid()
        )
    );

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_insight_chunks_updated_at 
    BEFORE UPDATE ON insight_chunks 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 添加注释
COMMENT ON TABLE insight_chunks IS '存储 insight 的文本分块数据';
COMMENT ON COLUMN insight_chunks.insight_id IS '关联的 insight ID';
COMMENT ON COLUMN insight_chunks.chunk_index IS '分块序号，从 0 开始';
COMMENT ON COLUMN insight_chunks.chunk_text IS '分块文本内容';
COMMENT ON COLUMN insight_chunks.chunk_size IS '分块大小（字符数）';
COMMENT ON COLUMN insight_chunks.estimated_tokens IS '预估的 token 数量';
COMMENT ON COLUMN insight_chunks.chunk_method IS '分块方法（character/recursive）';
COMMENT ON COLUMN insight_chunks.chunk_overlap IS '分块重叠大小';
COMMENT ON COLUMN insight_chunks.embedding IS '文本向量表示';
COMMENT ON COLUMN insight_chunks.embedding_model IS '生成 embedding 的模型';
COMMENT ON COLUMN insight_chunks.embedding_tokens IS '生成 embedding 消耗的 token 数';
COMMENT ON COLUMN insight_chunks.embedding_generated_at IS 'embedding 生成时间';

-- 创建相似度搜索函数
CREATE OR REPLACE FUNCTION find_similar_chunks(
    target_chunk_id UUID,
    similarity_threshold REAL DEFAULT 0.7,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    chunk_id UUID,
    insight_id UUID,
    chunk_index INTEGER,
    chunk_text TEXT,
    chunk_size INTEGER,
    similarity REAL
) AS $$
BEGIN
    RETURN QUERY
    WITH target_embedding AS (
        SELECT embedding
        FROM insight_chunks
        WHERE id = target_chunk_id
    )
    SELECT 
        ic.id as chunk_id,
        ic.insight_id,
        ic.chunk_index,
        ic.chunk_text,
        ic.chunk_size,
        (
            SELECT 1 - (ic.embedding <=> te.embedding) as similarity
            FROM target_embedding te
        ) as similarity
    FROM insight_chunks ic, target_embedding te
    WHERE ic.id != target_chunk_id
        AND ic.embedding IS NOT NULL
        AND te.embedding IS NOT NULL
        AND (1 - (ic.embedding <=> te.embedding)) >= similarity_threshold
    ORDER BY similarity DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- 创建基于文本搜索的相似度函数
CREATE OR REPLACE FUNCTION search_similar_chunks_by_text(
    search_text TEXT,
    user_id_param UUID,
    similarity_threshold REAL DEFAULT 0.7,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    chunk_id UUID,
    insight_id UUID,
    chunk_index INTEGER,
    chunk_text TEXT,
    chunk_size INTEGER,
    similarity REAL
) AS $$
BEGIN
    RETURN QUERY
    WITH search_embedding AS (
        -- 这里需要外部传入搜索文本的 embedding
        -- 暂时返回空，由应用层处理
        SELECT NULL::REAL[] as embedding
    )
    SELECT 
        ic.id as chunk_id,
        ic.insight_id,
        ic.chunk_index,
        ic.chunk_text,
        ic.chunk_size,
        0.0::REAL as similarity
    FROM insight_chunks ic
    JOIN insights i ON ic.insight_id = i.id
    WHERE i.user_id = user_id_param
        AND ic.embedding IS NOT NULL
    LIMIT 0; -- 暂时返回空结果，由应用层处理
END;
$$ LANGUAGE plpgsql;
