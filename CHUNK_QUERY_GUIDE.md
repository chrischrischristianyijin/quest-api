# 📚 分块数据查询使用指南

## 🎯 概述

Quest API 提供了强大的分块数据查询功能，支持多种查询方式和筛选条件，帮助您高效地检索和分析文本分块数据。

## 🔗 API 端点

所有分块查询接口都在 `/api/v1/insight-chunks` 路径下：

### 基础查询接口

#### 1. 获取指定 Insight 的分块数据
```http
GET /api/v1/insight-chunks/{insight_id}
```

**参数：**
- `insight_id` (路径参数): Insight ID
- `limit` (查询参数): 限制返回数量 (1-100)
- `offset` (查询参数): 偏移量 (默认0)

**示例：**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-api.com/api/v1/insight-chunks/123e4567-e89b-12d3-a456-426614174000?limit=10&offset=0"
```

#### 2. 获取分块摘要信息
```http
GET /api/v1/insight-chunks/{insight_id}/summary
```

**返回信息：**
- 总分块数
- 总字符数
- 总Token数
- 平均分块大小
- 分块方法

#### 3. 获取特定分块详情
```http
GET /api/v1/insight-chunks/{insight_id}/{chunk_index}
```

**参数：**
- `insight_id` (路径参数): Insight ID
- `chunk_index` (路径参数): 分块索引

### 🔍 语义搜索接口

#### 4. 基于文本搜索相似分块
```http
POST /api/v1/insight-chunks/search
```

**参数：**
- `query_text` (请求体): 搜索文本
- `similarity_threshold` (查询参数): 相似度阈值 (0.0-1.0, 默认0.7)
- `max_results` (查询参数): 最大返回结果数 (1-50, 默认10)

**示例：**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query_text": "人工智能的发展"}' \
  "https://your-api.com/api/v1/insight-chunks/search?similarity_threshold=0.8&max_results=20"
```

#### 5. 查找相似分块
```http
GET /api/v1/insight-chunks/{insight_id}/similar
```

**参数：**
- `insight_id` (路径参数): Insight ID
- `chunk_index` (查询参数): 参考分块索引
- `similarity_threshold` (查询参数): 相似度阈值 (0.0-1.0, 默认0.7)
- `max_results` (查询参数): 最大返回结果数 (1-50, 默认10)

### 🔧 高级搜索接口

#### 6. 高级分块搜索
```http
GET /api/v1/insight-chunks/search/advanced
```

**支持的筛选条件：**
- `insight_id`: 指定Insight ID
- `min_chunk_size`: 最小分块大小
- `max_chunk_size`: 最大分块大小
- `min_tokens`: 最小Token数
- `max_tokens`: 最大Token数
- `has_embedding`: 是否有Embedding
- `chunk_method`: 分块方法
- `created_after`: 创建时间之后 (ISO格式)
- `created_before`: 创建时间之前 (ISO格式)
- `limit`: 限制返回数量 (1-200, 默认50)
- `offset`: 偏移量 (默认0)

**示例：**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-api.com/api/v1/insight-chunks/search/advanced?min_chunk_size=1000&max_chunk_size=3000&has_embedding=true&limit=20"
```

### 📊 统计接口

#### 7. 获取分块统计信息
```http
GET /api/v1/insight-chunks/stats
```

**参数：**
- `insight_id` (查询参数): 指定Insight ID (可选)

**返回统计信息：**
- 总分块数
- 总字符数
- 总Token数
- 平均分块大小
- 平均Token数
- Embedding覆盖率
- 分块方法分布
- 大小分布
- Token分布

## 🚀 使用场景

### 1. RAG (检索增强生成)
```bash
# 搜索相关分块用于RAG
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query_text": "机器学习算法"}' \
  "https://your-api.com/api/v1/insight-chunks/search?similarity_threshold=0.7&max_results=5"
```

### 2. 内容分析
```bash
# 获取所有大分块的统计信息
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-api.com/api/v1/insight-chunks/search/advanced?min_chunk_size=2000&has_embedding=true"
```

### 3. 质量检查
```bash
# 检查没有Embedding的分块
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-api.com/api/v1/insight-chunks/search/advanced?has_embedding=false"
```

### 4. 时间范围查询
```bash
# 查询最近创建的分块
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-api.com/api/v1/insight-chunks/search/advanced?created_after=2024-01-01T00:00:00Z"
```

## 📋 响应格式

### 基础分块数据
```json
{
  "id": "chunk-uuid",
  "insight_id": "insight-uuid",
  "chunk_index": 0,
  "chunk_text": "分块文本内容...",
  "chunk_size": 1500,
  "estimated_tokens": 500,
  "chunk_method": "recursive",
  "chunk_overlap": 400,
  "embedding": [0.1, 0.2, ...],
  "embedding_model": "text-embedding-3-small",
  "embedding_tokens": 512,
  "embedding_generated_at": "2024-01-01T12:00:00Z",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### 搜索响应
```json
{
  "query_text": "搜索文本",
  "similarity_threshold": 0.7,
  "total_chunks_searched": 1000,
  "similar_chunks": [
    {
      "chunk_id": "chunk-uuid",
      "insight_id": "insight-uuid",
      "chunk_index": 2,
      "chunk_text": "相关分块内容...",
      "chunk_size": 1200,
      "similarity": 0.8542
    }
  ]
}
```

### 统计响应
```json
{
  "total_chunks": 150,
  "total_size": 225000,
  "total_tokens": 75000,
  "avg_chunk_size": 1500.0,
  "avg_tokens": 500.0,
  "chunks_with_embedding": 120,
  "embedding_coverage": 80.0,
  "chunk_methods": {
    "recursive": 150
  },
  "size_distribution": {
    "small (<500)": 10,
    "medium (500-1500)": 80,
    "large (1500-3000)": 50,
    "xlarge (>3000)": 10
  },
  "token_distribution": {
    "low (<200)": 5,
    "medium (200-500)": 60,
    "high (500-1000)": 70,
    "very_high (>1000)": 15
  },
  "scope": "all_insights"
}
```

## 🔐 认证要求

所有接口都需要Bearer Token认证：

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "https://your-api.com/api/v1/insight-chunks/..."
```

## ⚡ 性能优化建议

### 1. 分页查询
- 使用 `limit` 和 `offset` 参数进行分页
- 避免一次性查询大量数据

### 2. 筛选条件
- 使用高级搜索的筛选条件减少查询范围
- 优先使用 `insight_id` 限制查询范围

### 3. 语义搜索
- 合理设置 `similarity_threshold` (推荐0.7-0.8)
- 限制 `max_results` 数量

### 4. 缓存策略
- 统计信息可以缓存较长时间
- 频繁查询的数据考虑客户端缓存

## 🐛 错误处理

### 常见错误码
- `400`: 请求参数错误
- `401`: 认证失败
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器内部错误

### 错误响应格式
```json
{
  "success": false,
  "message": "错误描述",
  "statusCode": 400
}
```

## 📈 最佳实践

1. **合理使用分页**: 避免一次性加载大量数据
2. **优化搜索参数**: 根据实际需求调整相似度阈值
3. **定期检查统计**: 使用统计接口监控分块质量
4. **错误处理**: 实现适当的错误处理和重试机制
5. **性能监控**: 关注查询响应时间和资源使用

## 🔄 更新日志

- **v1.0.0**: 初始版本，支持基础查询和语义搜索
- **v1.1.0**: 添加高级搜索和统计功能
- **v1.2.0**: 优化RAG查询性能，调整分块大小配置

---

📞 **技术支持**: 如有问题，请联系开发团队或查看API文档。
