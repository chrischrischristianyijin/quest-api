# 🚀 增强RAG功能指南

## 📋 功能概述

Quest API的RAG系统现在支持在找到相关chunks后，自动添加对应的insight标题、URL和摘要作为上下文信息，并为前端提供完整的source信息。

## ✨ 新增功能

### 1. 增强的RAGChunk模型
```python
class RAGChunk(BaseModel):
    id: UUID
    insight_id: UUID
    chunk_index: int
    chunk_text: str
    chunk_size: int
    score: float
    created_at: datetime
    # 新增字段
    insight_title: Optional[str] = None      # insight标题
    insight_url: Optional[str] = None        # insight URL
    insight_summary: Optional[str] = None    # insight摘要
```

### 2. 增强的上下文构建
现在RAG上下文不仅包含chunk文本，还包含：
- **来源标题**: 帮助AI理解内容来源
- **来源链接**: 提供原始资源链接
- **内容摘要**: 提供更丰富的上下文信息

### 3. 完整的前端Source信息
前端现在可以获取到每个source的完整信息：
```json
{
  "sources": [
    {
      "id": "chunk-uuid",
      "insight_id": "insight-uuid", 
      "score": 0.85,
      "index": 1,
      "title": "人工智能发展趋势分析",
      "url": "https://example.com/ai-trends"
    }
  ]
}
```

## 🔄 工作流程

### 1. RAG检索流程
```
用户查询 → 生成查询embedding → 搜索相似chunks → 获取insight信息 → 构建增强上下文
```

### 2. 信息获取流程
```
搜索结果 → 提取唯一insight_id → 批量查询insights表 → 填充chunk信息 → 返回完整数据
```

## 📊 上下文格式示例

### 增强前的上下文
```
【1 | 0.85】人工智能是计算机科学的一个分支，它企图了解智能的实质...
【2 | 0.78】机器学习是人工智能的核心技术之一，通过算法让计算机...
```

### 增强后的上下文
```
【1 | 0.85】人工智能是计算机科学的一个分支，它企图了解智能的实质...
来源标题: 人工智能发展趋势分析
来源链接: https://example.com/ai-trends
内容摘要: 本文详细分析了人工智能技术的发展历程和未来趋势...

【2 | 0.78】机器学习是人工智能的核心技术之一，通过算法让计算机...
来源标题: 机器学习入门指南
来源链接: https://example.com/ml-guide
内容摘要: 机器学习是AI的重要组成部分，本文介绍了其基本概念和应用...
```

## 🎯 前端集成

### 1. 聊天响应格式
```javascript
// 非流式响应
{
  "success": true,
  "message": "聊天响应生成成功",
  "data": {
    "response": "AI回答内容...",
    "sources": [
      {
        "id": "chunk-uuid",
        "insight_id": "insight-uuid",
        "score": 0.85,
        "index": 1,
        "title": "人工智能发展趋势分析",
        "url": "https://example.com/ai-trends"
      }
    ],
    "request_id": "uuid",
    "latency_ms": 1500,
    "tokens_used": 150
  }
}

// 流式响应（在done事件中）
{
  "type": "done",
  "request_id": "uuid", 
  "latency_ms": 1500,
  "sources": [
    {
      "id": "chunk-uuid",
      "insight_id": "insight-uuid",
      "score": 0.85,
      "index": 1,
      "title": "人工智能发展趋势分析", 
      "url": "https://example.com/ai-trends"
    }
  ]
}
```

### 2. 前端使用示例
```javascript
// 处理聊天响应
function handleChatResponse(response) {
  const { response: aiResponse, sources } = response.data;
  
  // 显示AI回答
  displayAIResponse(aiResponse);
  
  // 显示来源信息
  displaySources(sources);
}

function displaySources(sources) {
  sources.forEach((source, index) => {
    const sourceElement = document.createElement('div');
    sourceElement.className = 'source-item';
    sourceElement.innerHTML = `
      <div class="source-header">
        <span class="source-number">[${index + 1}]</span>
        <span class="source-title">${source.title || '无标题'}</span>
        <span class="source-score">${(source.score * 100).toFixed(1)}%</span>
      </div>
      ${source.url ? `<a href="${source.url}" target="_blank" class="source-link">查看原文</a>` : ''}
    `;
    
    document.getElementById('sources-container').appendChild(sourceElement);
  });
}
```

## 🛠️ 技术实现

### 1. RAG服务增强
```python
class RAGService:
    async def _process_hnsw_results(self, results: List[Dict], k: int) -> List[RAGChunk]:
        # 处理搜索结果
        filtered_chunks = self._filter_and_sort_chunks(results, k)
        
        # 获取insight信息
        unique_insight_ids = list(set(str(chunk.insight_id) for chunk in filtered_chunks))
        insights_info = await self._get_insights_info(unique_insight_ids)
        
        # 填充insight信息到chunks
        for chunk in filtered_chunks:
            insight_info = insights_info.get(str(chunk.insight_id), {})
            chunk.insight_title = insight_info.get('title')
            chunk.insight_url = insight_info.get('url')
            chunk.insight_summary = insight_info.get('summary')
        
        return filtered_chunks
    
    async def _get_insights_info(self, insight_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量获取insight信息"""
        response = self.supabase.table('insights').select('id, title, url, summary').in_('id', insight_ids).execute()
        
        insights_info = {}
        for insight in response.data:
            insights_info[insight['id']] = {
                'title': insight.get('title'),
                'url': insight.get('url'), 
                'summary': insight.get('summary')
            }
        
        return insights_info
```

### 2. 上下文格式化增强
```python
def format_context(self, chunks: List[RAGChunk], max_tokens: int = 4000) -> RAGContext:
    context_parts = []
    
    for i, chunk in enumerate(sorted_chunks):
        chunk_parts = [f"【{i+1} | {chunk.score:.2f}】{chunk.chunk_text}"]
        
        if chunk.insight_title:
            chunk_parts.append(f"来源标题: {chunk.insight_title}")
        
        if chunk.insight_url:
            chunk_parts.append(f"来源链接: {chunk.insight_url}")
            
        if chunk.insight_summary and chunk.insight_summary.strip():
            chunk_parts.append(f"内容摘要: {chunk.insight_summary}")
        
        context_text = "\n".join(chunk_parts)
        context_parts.append(context_text)
    
    return RAGContext(chunks=chunks, context_text="\n\n".join(context_parts))
```

## 📈 性能优化

### 1. 批量查询
- 使用`in_`查询批量获取insight信息
- 避免N+1查询问题
- 减少数据库连接次数

### 2. 缓存策略
- 可以考虑对insight信息进行缓存
- 减少重复查询的开销

### 3. 异步处理
- 所有数据库查询都是异步的
- 不阻塞主流程

## 🧪 测试

### 运行测试脚本
```bash
python test_enhanced_rag.py
```

### 测试内容
1. **RAG检索功能**: 验证是否能正确检索到相关chunks
2. **Insight信息获取**: 验证是否能正确获取标题、URL和摘要
3. **上下文格式化**: 验证增强后的上下文格式
4. **前端Source格式**: 验证返回给前端的source信息格式

## 🎯 优势总结

### 1. 更丰富的上下文
- AI可以获得更多关于内容来源的信息
- 提高回答的准确性和相关性

### 2. 更好的用户体验
- 前端可以显示来源标题和链接
- 用户可以点击查看原始内容
- 提供更好的可追溯性

### 3. 保持性能
- 批量查询优化了数据库访问
- 异步处理不阻塞响应
- 向后兼容现有功能

## 🔮 未来规划

### 短期优化
- [ ] 添加insight信息缓存
- [ ] 优化批量查询性能
- [ ] 添加更多insight元数据

### 长期规划
- [ ] 支持多模态内容（图片、视频等）
- [ ] 智能摘要生成
- [ ] 个性化推荐算法

## 📞 技术支持

如有问题或建议，请查看：
- API文档: `/docs`
- 测试脚本: `test_enhanced_rag.py`
- 日志输出: 查看应用日志获取详细信息
