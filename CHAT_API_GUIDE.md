# 🤖 AI聊天API使用指南

## 📋 概述

Quest API 现在支持基于RAG（检索增强生成）的AI聊天功能，可以基于您的文档库进行智能问答。

## 🔗 API端点

### 1. 聊天接口

**POST** `/api/v1/chat`

**功能**: 与AI助手进行对话，支持RAG检索和流式响应

**请求头**:
```http
Content-Type: application/json
Authorization: Bearer {token}  # 可选，用于用户身份识别
```

**请求体**:
```json
{
  "message": "什么是人工智能？"
}
```

**参数说明**:
- `message`: 用户问题（必需）

**注意**: 
- RAG检索完全自动化，无需手动配置
- 所有其他参数（流式响应、检索数量、相似度阈值等）都由后端自动调节
- 用户只需发送问题即可获得智能回答

### 2. 健康检查

**GET** `/api/v1/chat/health`

**功能**: 检查聊天服务状态

**响应示例**:
```json
{
  "status": "healthy",
  "message": "聊天服务运行正常",
  "timestamp": "2024-01-15T10:30:00Z",
  "features": {
    "rag_enabled": true,
    "streaming_enabled": true,
    "rate_limiting_enabled": true
  }
}
```

## 🔄 响应格式

### 流式响应 (SSE)

当 `stream=true` 时，返回 `text/event-stream` 格式：

```
data: {"type": "content", "content": "人工智能是"}

data: {"type": "content", "content": "一门计算机科学"}

data: {"type": "done", "request_id": "uuid", "latency_ms": 1500, "sources": [...]}
```

### 非流式响应

当 `stream=false` 时，返回JSON格式：

```json
{
  "success": true,
  "message": "聊天响应生成成功",
  "data": {
    "response": "人工智能是一门计算机科学分支...",
    "sources": [
      {
        "id": "chunk-uuid",
        "insight_id": "insight-uuid",
        "score": 0.85,
        "index": 2
      }
    ],
    "request_id": "uuid",
    "latency_ms": 1500,
    "tokens_used": 150
  }
}
```

## 🚀 使用示例

### JavaScript/TypeScript

```javascript
// 流式聊天
async function chatWithStream(question) {
  const response = await fetch('/api/v1/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer your-token'
    },
    body: JSON.stringify({
      message: question
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        
        if (data.type === 'content') {
          console.log('AI:', data.content);
        } else if (data.type === 'done') {
          console.log('Sources:', data.sources);
          console.log('Latency:', data.latency_ms + 'ms');
        }
      }
    }
  }
}

// 使用示例
const question = '请介绍一下机器学习的基本概念';
chatWithStream(question);
```

### Python

```python
import requests
import json

def chat_with_rag(query, token=None):
    url = "https://your-api.com/api/v1/chat"
    headers = {
        "Content-Type": "application/json"
    }
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    data = {
        "message": query
    }
    
    response = requests.post(url, json=data, headers=headers)
    return response.json()

# 使用示例
result = chat_with_rag("什么是深度学习？")
print("AI回答:", result["data"]["response"])
print("引用来源:", result["data"]["sources"])
```

### cURL

```bash
# 流式聊天
curl -X POST "https://your-api.com/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "message": "请解释一下神经网络的工作原理"
  }' \
  --no-buffer
```

## 🔐 认证与权限

### 用户身份识别

- **有认证**: 传入 `Authorization: Bearer {user_id}:{token}` 格式
- **无认证**: 可以匿名使用，但只能访问公开内容

### 限流策略

- **频率限制**: 每IP/用户每分钟最多30次请求
- **错误码**: 429 Too Many Requests

## 📊 RAG检索机制

### 检索流程

1. **文本嵌入**: 使用 `text-embedding-3-small` 将用户问题向量化
2. **相似度检索**: 调用Supabase RPC函数进行余弦相似度搜索
3. **上下文构建**: 将检索到的分块格式化为上下文
4. **AI生成**: 将上下文和问题一起发送给GPT-4o-mini生成回答

### 上下文格式

```
【1 | 0.85】第一个相关分块的内容...

【2 | 0.78】第二个相关分块的内容...

【3 | 0.72】第三个相关分块的内容...
```

### 引用编号

AI回答中会自动包含引用编号，如：
- "根据文档内容 [1][2]，人工智能是..."
- "机器学习算法 [3] 通常包括..."

## ⚙️ 配置参数

### 环境变量

```bash
# OpenAI配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
CHAT_MODEL=gpt-4o-mini

# RAG配置
RAG_ENABLED=true
RAG_DEFAULT_K=6
RAG_DEFAULT_MIN_SCORE=0.2
RAG_MAX_CONTEXT_TOKENS=2000

# 限流配置
RATE_LIMIT_REQUESTS_PER_MINUTE=30
```

### 参数调优建议

- **k值**: 6-10个分块通常效果最好
- **min_score**: 0.2-0.3适合大多数场景
- **temperature**: 0.3-0.5保持回答的准确性
- **max_context_tokens**: 2000-3000平衡质量和成本

## 🐛 错误处理

### 常见错误码

- `400`: 请求参数错误
- `401`: 认证失败
- `429`: 请求过于频繁
- `500`: 服务器内部错误

### 错误响应格式

```json
{
  "code": "CHAT_ERROR",
  "message": "聊天服务暂时不可用: 具体错误信息",
  "request_id": "uuid"
}
```

## 📈 性能优化

### 建议

1. **使用流式响应**: 提供更好的用户体验
2. **合理设置k值**: 避免检索过多无关内容
3. **调整min_score**: 根据数据质量调整阈值
4. **缓存机制**: 对常见问题实现客户端缓存

### 监控指标

- **延迟**: 端到端响应时间
- **Token使用**: 输入和输出token数量
- **检索质量**: 相似度分数分布
- **错误率**: 请求失败比例

## 🔄 更新日志

- **v1.0.0**: 初始版本，支持基础RAG聊天
- **v1.1.0**: 添加流式响应支持
- **v1.2.0**: 优化检索算法和上下文构建

---

📞 **技术支持**: 如有问题，请联系开发团队或查看API文档。
