# 🚀 数据库性能优化建议

## 📊 **必需的数据库索引**

为了显著提升查询性能，建议在 Supabase 中创建以下索引：

### 1. **insights 表索引**
```sql
-- 用户ID索引（最重要）
CREATE INDEX IF NOT EXISTS idx_insights_user_id ON insights(user_id);

-- 更新时间索引（用于增量查询）
CREATE INDEX IF NOT EXISTS idx_insights_updated_at ON insights(updated_at DESC);

-- 复合索引：用户ID + 更新时间（用于增量查询）
CREATE INDEX IF NOT EXISTS idx_insights_user_updated ON insights(user_id, updated_at DESC);

-- 创建时间索引（用于分页排序）
CREATE INDEX IF NOT EXISTS idx_insights_created_at ON insights(created_at DESC);

-- 复合索引：用户ID + 创建时间（用于用户数据分页）
CREATE INDEX IF NOT EXISTS idx_insights_user_created ON insights(user_id, created_at DESC);

-- 全文搜索索引（用于标题和描述搜索）
CREATE INDEX IF NOT EXISTS idx_insights_search ON insights USING gin(to_tsvector('english', title || ' ' || description));
```

### 2. **insight_tags 表索引**
```sql
-- insight_id 索引（用于标签查询）
CREATE INDEX IF NOT EXISTS idx_insight_tags_insight_id ON insight_tags(insight_id);

-- user_id 索引（用于权限过滤）
CREATE INDEX IF NOT EXISTS idx_insight_tags_user_id ON insight_tags(user_id);

-- tag_id 索引（用于反向查询）
CREATE INDEX IF NOT EXISTS idx_insight_tags_tag_id ON insight_tags(tag_id);

-- 复合索引：insight_id + user_id（最常用的查询组合）
CREATE INDEX IF NOT EXISTS idx_insight_tags_insight_user ON insight_tags(insight_id, user_id);
```

### 3. **user_tags 表索引**
```sql
-- user_id 索引
CREATE INDEX IF NOT EXISTS idx_user_tags_user_id ON user_tags(user_id);

-- 复合索引：user_id + name（用于标签查找）
CREATE INDEX IF NOT EXISTS idx_user_tags_user_name ON user_tags(user_id, name);

-- 创建时间索引（用于排序）
CREATE INDEX IF NOT EXISTS idx_user_tags_created_at ON user_tags(created_at DESC);
```

### 4. **insight_contents 表索引**
```sql
-- insight_id 索引（用于内容查询）
CREATE INDEX IF NOT EXISTS idx_insight_contents_insight_id ON insight_contents(insight_id);

-- user_id 索引（用于权限过滤）
CREATE INDEX IF NOT EXISTS idx_insight_contents_user_id ON insight_contents(user_id);

-- URL 索引（用于缓存查找）
CREATE INDEX IF NOT EXISTS idx_insight_contents_url ON insight_contents(url);

-- 创建时间索引（用于排序）
CREATE INDEX IF NOT EXISTS idx_insight_contents_created_at ON insight_contents(created_at DESC);
```

## ⚡ **查询优化策略**

### 1. **避免 SELECT ***
- ✅ 只选择需要的字段
- ❌ 避免 `SELECT *`，特别是有大字段的表

### 2. **使用复合索引**
- 将最常用的查询条件组合创建复合索引
- 索引字段顺序很重要：选择性高的字段放前面

### 3. **分页优化**
```sql
-- ✅ 使用 LIMIT + OFFSET（小数据量）
SELECT * FROM insights WHERE user_id = ? ORDER BY created_at DESC LIMIT 20 OFFSET 0;

-- ✅ 使用游标分页（大数据量）
SELECT * FROM insights WHERE user_id = ? AND created_at < ? ORDER BY created_at DESC LIMIT 20;
```

### 4. **JOIN 优化**
```sql
-- ✅ 使用 INNER JOIN 而不是多次查询
SELECT i.*, ut.name as tag_name, ut.color as tag_color
FROM insights i
LEFT JOIN insight_tags it ON i.id = it.insight_id
LEFT JOIN user_tags ut ON it.tag_id = ut.id
WHERE i.user_id = ?;
```

## 🔧 **连接池配置**

在 `render.yaml` 中添加数据库连接池配置：

```yaml
envVars:
  - key: DB_POOL_SIZE
    value: 20
  - key: DB_MAX_OVERFLOW
    value: 10
  - key: DB_POOL_TIMEOUT
    value: 30
```

## 📈 **性能监控**

### 1. **慢查询监控**
在 Supabase Dashboard 中启用慢查询日志：
- 查询时间 > 1000ms 的查询
- 定期检查和优化

### 2. **索引使用情况**
```sql
-- 检查索引使用情况
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### 3. **表统计信息**
```sql
-- 检查表大小和行数
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, n_dead_tup
FROM pg_stat_user_tables
WHERE schemaname = 'public';
```

## 🎯 **预期性能提升**

创建这些索引后，预期性能提升：

| 查询类型 | 优化前 | 优化后 | 提升 |
|----------|--------|--------|------|
| 用户 insights 列表 | 500-2000ms | 50-200ms | 5-10x |
| 标签查询 | 200-800ms | 20-80ms | 10x |
| 搜索查询 | 1000-5000ms | 100-500ms | 10x |
| 增量查询 | 300-1000ms | 30-100ms | 10x |

## 🚨 **注意事项**

1. **索引维护成本**: 索引会稍微降低写入性能
2. **存储空间**: 索引会占用额外存储空间
3. **定期维护**: 需要定期 `ANALYZE` 表以更新统计信息
4. **监控**: 定期检查索引使用情况，删除未使用的索引
