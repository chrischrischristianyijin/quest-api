# Vector(1536) 迁移指南

## 概述

本指南说明如何将现有的 `REAL[]` 类型迁移到 `vector(1536)` 类型，以支持高效的向量相似度搜索。

## 迁移步骤

### 1. 安装 pgvector 扩展

确保PostgreSQL数据库已安装pgvector扩展：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. 选择迁移策略

#### 策略A：创建新表（推荐）

使用 `create_vector_tables.sql` 创建新的表结构：

```bash
# 在Supabase SQL编辑器中执行
psql -f database/migrations/create_vector_tables.sql
```

#### 策略B：修改现有表

使用 `update_embedding_to_vector.sql` 修改现有表：

```bash
# 在Supabase SQL编辑器中执行
psql -f database/migrations/update_embedding_to_vector.sql
```

### 3. 更新应用代码

确保应用代码正确处理vector类型：

- ✅ `insights_service.py` - 已更新，支持vector(1536)存储
- ✅ `rag_service.py` - 已更新，支持vector查询
- ✅ 数据库迁移脚本 - 已创建

### 4. 验证迁移

运行测试脚本验证迁移是否成功：

```bash
python test_vector_storage.py
```

## 关键变化

### 数据库层面

1. **列类型变更**：
   ```sql
   -- 之前
   embedding REAL[]
   
   -- 之后
   embedding vector(1536)
   ```

2. **索引优化**：
   ```sql
   -- 添加HNSW索引
   CREATE INDEX idx_insight_chunks_embedding_hnsw 
   ON insight_chunks USING hnsw (embedding vector_cosine_ops);
   ```

3. **查询方式**：
   - 使用Python端相似度计算
   - 简单可靠，易于调试

### 应用层面

1. **存储格式**：
   - 直接传递Python列表给Supabase
   - Supabase自动转换为vector(1536)

2. **查询方式**：
   - 使用Python端相似度计算
   - 简单可靠，易于调试

3. **距离计算**：
   - 使用numpy计算余弦相似度
   - 相似度 = dot_product / (norm1 * norm2)

## 性能优势

### 1. 查询性能

- **HNSW索引**：支持近似最近邻搜索（如果使用）
- **Python计算**：灵活可控的相似度计算
- **简单架构**：无需复杂的RPC函数

### 2. 存储效率

- **压缩存储**：vector类型比REAL[]更高效
- **类型安全**：强制1536维度限制
- **索引友好**：专为向量搜索优化

## 注意事项

### 1. 数据一致性

确保以下三个一致：

- ✅ **模型一致**：`text-embedding-3-small`
- ✅ **维度一致**：1536
- ✅ **距离一致**：余弦距离 `<=>`

### 2. 迁移风险

- **数据丢失**：迁移前请备份数据
- **服务中断**：建议在维护窗口执行
- **回滚计划**：准备回滚方案

### 3. 测试验证

- **功能测试**：验证RAG检索正常
- **性能测试**：对比查询性能
- **数据完整性**：检查数据无丢失

## 故障排除

### 1. 常见错误

```sql
-- 错误：类型不匹配
ERROR: operator does not exist: real[] <=> vector

-- 解决：确保使用vector(1536)类型
```

### 2. 性能问题

```sql
-- 检查索引是否创建
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'insight_chunks' 
AND indexname LIKE '%hnsw%';
```

### 3. 数据验证

```sql
-- 检查vector数据
SELECT id, array_length(embedding, 1) as dims
FROM insight_chunks 
WHERE embedding IS NOT NULL
LIMIT 5;
```

## 监控指标

### 1. 查询性能

- 平均查询时间
- 索引命中率
- 内存使用情况

### 2. 数据质量

- embedding维度分布
- 相似度分数范围
- 检索结果相关性

## 总结

迁移到 `vector(1536)` 类型将显著提升向量搜索性能，支持更高效的RAG检索。请按照本指南逐步执行迁移，并充分测试验证。
