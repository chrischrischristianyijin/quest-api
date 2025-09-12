-- 创建基于向量的HNSW搜索函数
-- 这个函数使用pgvector的HNSW索引进行高效的向量相似度搜索

-- 1. 确保安装了pgvector扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 创建向量搜索函数
CREATE OR REPLACE FUNCTION search_similar_chunks_by_vector(
    query_embedding vector(1536),
    user_id_param uuid,
    similarity_threshold real DEFAULT 0.7,
    max_results integer DEFAULT 10
)
RETURNS TABLE(
    chunk_id uuid,
    insight_id uuid,
    chunk_index integer,
    chunk_text text,
    chunk_size integer,
    similarity real,
    created_at timestamp with time zone
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ic.id as chunk_id,
        ic.insight_id,
        ic.chunk_index,
        ic.chunk_text,
        ic.chunk_size,
        (1 - (ic.embedding <=> query_embedding)) as similarity,
        ic.created_at
    FROM insight_chunks ic
    INNER JOIN insights i ON ic.insight_id = i.id
    WHERE i.user_id = user_id_param
    AND ic.embedding IS NOT NULL
    AND (1 - (ic.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY ic.embedding <=> query_embedding
    LIMIT max_results;
END;
$$;

-- 3. 添加函数注释
COMMENT ON FUNCTION search_similar_chunks_by_vector(vector(1536), uuid, real, integer) 
IS '使用HNSW索引进行向量相似度搜索，返回用户insights中最相似的分块';

-- 4. 创建索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_insight_chunks_embedding_hnsw 
ON insight_chunks USING hnsw (embedding vector_cosine_ops);

-- 5. 创建用户insights的索引（优化JOIN性能）
CREATE INDEX IF NOT EXISTS idx_insights_user_id 
ON insights (user_id);

-- 6. 验证函数创建成功
-- 可以通过以下查询测试函数：
-- SELECT * FROM search_similar_chunks_by_vector('[0.1,0.2,0.3,...]'::vector(1536), 'user-uuid-here', 0.7, 10);
