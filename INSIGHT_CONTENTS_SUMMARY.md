# 🗄️ 摘要缓存与 insight_contents 表集成

## 📋 功能概述

我们实现了一个智能的摘要管理系统：元数据提取时生成摘要并缓存，创建 insight 时从缓存获取摘要并保存到 `insight_contents` 表中。这样既避免了重复生成摘要，又确保了摘要与具体的 insight 关联。

## 🗃️ 使用现有表结构

### `insight_contents` 表
使用现有的 `insight_contents` 表，其中包含：
- `url` - 网页URL
- `summary` - AI生成的摘要内容
- `text` - 网页文本内容
- `html` - 网页HTML内容
- `extracted_at` - 提取时间
- 其他现有字段...

## 🔄 工作流程

### 1. 元数据提取流程
```
用户调用元数据提取 → 提取元数据 → 启动后台摘要任务 → 立即返回元数据
```

### 2. 摘要生成和缓存流程
```
后台任务启动 → 获取页面内容 → 调用 OpenAI API → 生成摘要 → 保存到缓存
```

### 3. Insight 创建 Pipeline
```
用户创建 insight → 启动完整的内容处理 pipeline：
├── 1. 检查缓存中是否有摘要
├── 2. 抓取页面内容（无论是否有缓存）
├── 3. 生成摘要（如果缓存中没有）
├── 4. 准备内容数据
├── 5. 数据清理和验证
└── 6. 保存到 insight_contents 表
```

### 4. 状态查询流程
```
用户查询摘要状态 → 从缓存查询 → 返回结果
```

## 🛠️ 技术实现

### 1. 摘要缓存管理
```python
# 缓存结构
summary_cache = {
    "url": {
        "status": "completed|generating|failed",
        "created_at": datetime,
        "summary": "生成的摘要内容",
        "error": "错误信息（如果有）"
    }
}
```

### 2. 元数据提取时生成摘要
```python
# 后台异步生成摘要
async def generate_summary_background(url: str, metadata: Dict[str, Any]):
    # 获取页面内容
    page_content = await fetch_page_content(url)
    # 生成摘要
    summary = await generate_summary(text_content)
    # 保存到缓存
    summary_cache[url] = {
        'status': 'completed',
        'created_at': datetime.now(),
        'summary': summary,
        'error': None
    }
```

### 3. Insight 创建 Pipeline
```python
async def _fetch_and_save_content(insight_id: UUID, user_id: UUID, url: str):
    """完整的 insight 内容处理 pipeline"""
    
    # 1. 检查缓存中是否有摘要
    cached_summary = None
    if url in summary_cache and summary_cache[url]['status'] == 'completed':
        cached_summary = summary_cache[url]['summary']
    
    # 2. 抓取页面内容（无论是否有缓存）
    page = await fetch_page_content(url)
    
    # 3. 生成摘要（如果缓存中没有）
    summary_text = cached_summary
    if not summary_text:
        summary_text = await generate_summary(source_text)
        # 更新缓存
        summary_cache[url] = {
            'status': 'completed',
            'created_at': datetime.now(),
            'summary': summary_text,
            'error': None
        }
    
    # 4. 准备内容数据
    content_payload = {
        'insight_id': str(insight_id),
        'user_id': str(user_id),
        'url': url,
        'html': page.get('html'),
        'text': page.get('text'),
        'summary': summary_text,
        # ... 其他字段
    }
    
    # 5. 数据清理和验证
    safe_payload = _sanitize_for_pg(content_payload)
    
    # 6. 保存到数据库
    supabase_service.table('insight_contents').insert(safe_payload).execute()
```

## 📊 状态说明

| 状态 | 说明 |
|------|------|
| `completed` | 摘要生成完成，已保存到数据库 |
| `generating` | 摘要正在生成中 |
| `not_found` | 未找到摘要记录 |

## 🧪 测试方法

### 1. 基本功能测试
```bash
python3 test_metadata_summary.py
```

### 2. 手动测试
```bash
# 1. 提取元数据（触发摘要生成）
curl -X POST "https://quest-api-edz1.onrender.com/api/v1/metadata/extract" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "url=https://example.com"

# 2. 等待15-20秒让摘要生成和保存

# 3. 查询摘要状态
curl "https://quest-api-edz1.onrender.com/api/v1/metadata/summary/https%3A%2F%2Fexample.com"
```

### 3. 数据库验证
```sql
-- 查看 insight_contents 表中的摘要
SELECT url, summary, extracted_at 
FROM insight_contents 
WHERE summary IS NOT NULL 
ORDER BY extracted_at DESC 
LIMIT 5;
```

## 📈 优势

### 1. 完整的 Pipeline 处理
- **统一流程**：所有 insight 创建都经过相同的处理流程
- **智能缓存**：避免重复生成摘要，提高性能
- **数据完整性**：确保所有必要的数据都被正确处理

### 2. 智能缓存机制
- **避免重复生成**：相同URL的摘要只生成一次
- **提高性能**：减少 OpenAI API 调用次数
- **节省成本**：降低 API 使用费用

### 3. 数据关联性
- **与 insight 关联**：摘要与具体的 insight 关联
- **用户隔离**：每个用户的 insight 独立管理
- **数据一致性**：确保摘要与内容的一致性

### 4. 系统可靠性
- **容错机制**：每个步骤都有错误处理
- **状态跟踪**：完整的状态生命周期管理
- **日志记录**：详细的处理过程日志

## 🎉 总结

通过完整的 Pipeline 设计，我们实现了：

1. ✅ **完整的处理流程**：每个 insight 创建都经过统一的 6 步 pipeline
2. ✅ **智能缓存机制**：元数据提取时生成摘要并缓存
3. ✅ **智能复用**：创建 insight 时优先使用缓存的摘要
4. ✅ **数据完整性**：确保所有必要的数据都被正确处理和保存
5. ✅ **性能优化**：避免重复生成摘要，节省 API 调用

现在你的摘要系统既完整又智能：元数据提取时生成摘要，创建 insight 时通过完整的 pipeline 处理，智能地使用缓存摘要并保存到 `insight_contents` 表中！
