-- 修改现有insight_chunks表支持vector(1536)
-- 这个脚本会修改现有表，将embedding列从REAL[]改为vector(1536)

-- 1. 确保安装了pgvector扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 备份现有数据（可选，建议在生产环境执行前先备份）
-- CREATE TABLE insight_chunks_backup AS SELECT * FROM insight_chunks;

-- 3. 添加新的vector列
ALTER TABLE insight_chunks ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- 4. 将现有的REAL[]数据转换为vector(1536)（如果存在）
UPDATE insight_chunks 
SET embedding_new = embedding::vector(1536)
WHERE embedding IS NOT NULL AND embedding_new IS NULL;

-- 5. 删除旧的embedding列
ALTER TABLE insight_chunks DROP COLUMN IF EXISTS embedding;

-- 6. 重命名新列为embedding
ALTER TABLE insight_chunks RENAME COLUMN embedding_new TO embedding;

-- 7. 确保表结构完整（添加缺失的列）
ALTER TABLE insight_chunks ADD COLUMN IF NOT EXISTS estimated_tokens INTEGER;
ALTER TABLE insight_chunks ADD COLUMN IF NOT EXISTS chunk_method VARCHAR(50) DEFAULT 'recursive';
ALTER TABLE insight_chunks ADD COLUMN IF NOT EXISTS chunk_overlap INTEGER DEFAULT 200;
ALTER TABLE insight_chunks ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100);
ALTER TABLE insight_chunks ADD COLUMN IF NOT EXISTS embedding_tokens INTEGER;
ALTER TABLE insight_chunks ADD COLUMN IF NOT EXISTS embedding_generated_at TIMESTAMP WITH TIME ZONE;

-- 8. 创建HNSW向量索引
CREATE INDEX IF NOT EXISTS idx_insight_chunks_embedding_hnsw 
ON insight_chunks USING hnsw (embedding vector_cosine_ops);

-- 9. 添加注释
COMMENT ON COLUMN insight_chunks.embedding IS '文本向量表示 (vector(1536))';

-- 10. 验证数据完整性
-- 检查是否有数据丢失
-- SELECT COUNT(*) FROM insight_chunks WHERE embedding IS NOT NULL;