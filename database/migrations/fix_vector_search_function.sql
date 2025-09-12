-- 修复向量搜索函数的返回类型问题
-- 将similarity列从real改为double precision

-- 删除现有函数（如果存在）
DROP FUNCTION IF EXISTS search_similar_chunks_by_vector(vector(1536), uuid, real, integer);

-- 重新创建函数，使用正确的返回类型
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
    similarity double precision,
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
        (1 - (ic.embedding <=> query_embedding))::double precision as similarity,
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

-- 添加函数注释
COMMENT ON FUNCTION search_similar_chunks_by_vector(vector(1536), uuid, real, integer) 
IS '使用HNSW索引进行向量相似度搜索，返回用户insights中最相似的分块。similarity列返回double precision类型。';

-- 验证函数
-- SELECT * FROM search_similar_chunks_by_vector('[0.1,0.2,0.3]'::vector(1536), '00000000-0000-0000-0000-000000000000'::uuid, 0.7, 10);
