# 🔧 OpenAI API 配置指南

## 🚨 问题描述

你遇到的错误：
```json
{
  "error": {
    "message": "Missing bearer or basic authentication in header",
    "type": "invalid_request_error",
    "param": null,
    "code": null
  }
}
```

这个错误表明 **OpenAI API 请求缺少认证头**，通常是因为：
1. 没有配置 `OPENAI_API_KEY` 环境变量
2. API 密钥无效或已过期
3. 环境变量没有正确加载

## 🔧 解决方案

### 方案1：本地开发环境配置

#### 1. 创建 `.env` 文件
在项目根目录创建 `.env` 文件：

```env
# OpenAI API 配置
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
SUMMARY_ENABLED=true
SUMMARY_PROVIDER=openai
SUMMARY_MODEL=gpt-3.5-turbo
SUMMARY_MAX_TOKENS=220
SUMMARY_INPUT_CHAR_LIMIT=12000
SUMMARY_CHUNK_CHAR_LIMIT=4000
SUMMARY_MAX_CHUNKS=8
SUMMARY_TEMPERATURE=0.3

# 其他配置...
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

#### 2. 获取 OpenAI API 密钥
1. 访问 [OpenAI Platform](https://platform.openai.com/api-keys)
2. 登录你的账户
3. 点击 "Create new secret key"
4. 复制生成的密钥（以 `sk-` 开头）
5. 将密钥粘贴到 `.env` 文件的 `OPENAI_API_KEY` 字段

### 方案2：Render 生产环境配置

#### 1. 通过 Render Dashboard 配置

1. 登录 [Render Dashboard](https://dashboard.render.com)
2. 找到你的 `quest-api` 服务
3. 点击 "Environment" 标签
4. 添加以下环境变量：

| 变量名 | 值 | 说明 |
|--------|----|----|
| `OPENAI_API_KEY` | `sk-your-actual-api-key-here` | **必需** - 你的 OpenAI API 密钥 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | 可选 - API 基础URL |
| `SUMMARY_ENABLED` | `true` | 启用摘要功能 |
| `SUMMARY_PROVIDER` | `openai` | 使用 OpenAI 作为提供商 |
| `SUMMARY_MODEL` | `gpt-3.5-turbo` | 使用的模型 |
| `SUMMARY_MAX_TOKENS` | `220` | 最大输出令牌数 |
| `SUMMARY_INPUT_CHAR_LIMIT` | `12000` | 输入字符限制 |
| `SUMMARY_CHUNK_CHAR_LIMIT` | `4000` | 分块字符限制 |
| `SUMMARY_MAX_CHUNKS` | `8` | 最大分块数 |
| `SUMMARY_TEMPERATURE` | `0.3` | 生成温度 |

#### 2. 重新部署
配置完成后，Render 会自动重新部署你的应用。

### 方案3：使用其他 LLM 提供商

如果你不想使用 OpenAI，可以配置其他兼容的 LLM 提供商：

#### 使用 Azure OpenAI
```env
OPENAI_API_KEY=your-azure-api-key
OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment-name
```

#### 使用本地部署的模型
```env
OPENAI_API_KEY=not-needed
OPENAI_BASE_URL=http://localhost:8000/v1
SUMMARY_MODEL=your-local-model-name
```

## 🔍 验证配置

### 1. 检查环境变量
```bash
# 本地开发
python -c "import os; print('OPENAI_API_KEY:', os.getenv('OPENAI_API_KEY', 'NOT_SET'))"

# 或者在代码中添加调试日志
```

### 2. 测试 API 调用
创建一个简单的测试脚本：

```python
import os
import httpx

async def test_openai_api():
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    
    if not api_key:
        print("❌ OPENAI_API_KEY 未设置")
        return
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    
    payload = {
        'model': 'gpt-3.5-turbo',
        'messages': [
            {'role': 'user', 'content': 'Hello, this is a test.'}
        ],
        'max_tokens': 50
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            print("✅ API 调用成功")
            print(response.json())
    except Exception as e:
        print(f"❌ API 调用失败: {e}")

# 运行测试
import asyncio
asyncio.run(test_openai_api())
```

## 🛠️ 故障排除

### 常见问题

1. **API 密钥无效**
   - 检查密钥是否正确复制
   - 确认密钥没有过期
   - 验证账户余额是否充足

2. **网络连接问题**
   - 检查防火墙设置
   - 确认网络连接正常
   - 尝试使用 VPN

3. **环境变量未加载**
   - 重启应用服务器
   - 检查 `.env` 文件格式
   - 确认文件路径正确

4. **配额限制**
   - 检查 OpenAI 账户配额
   - 考虑升级账户计划
   - 使用更便宜的模型

### 调试步骤

1. **检查日志**
   ```bash
   # 查看应用日志
   tail -f logs/app.log
   ```

2. **验证环境变量**
   ```python
   import os
   print("环境变量检查:")
   print(f"OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
   print(f"SUMMARY_ENABLED: {os.getenv('SUMMARY_ENABLED')}")
   print(f"SUMMARY_PROVIDER: {os.getenv('SUMMARY_PROVIDER')}")
   ```

3. **测试网络连接**
   ```bash
   curl -I https://api.openai.com/v1/models
   ```

## 📝 注意事项

1. **安全性**：永远不要在代码中硬编码 API 密钥
2. **成本控制**：设置使用限制和监控
3. **备份**：保存多个 API 密钥作为备用
4. **版本兼容**：确保使用的模型版本与你的需求匹配

## 🚀 下一步

配置完成后，你的应用应该能够正常调用 OpenAI API 进行文本摘要生成。如果仍有问题，请检查：

1. 应用日志中的详细错误信息
2. OpenAI 账户状态和配额
3. 网络连接和防火墙设置
4. 环境变量是否正确加载
