# Quest API 部署指南

## 🚀 本地开发环境配置

在开始部署之前，你需要先配置本地开发环境：

### 1. 创建环境配置文件

在项目根目录创建 `.env` 文件：

```bash
# 复制示例文件
cp .env.example .env

# 或者手动创建
touch .env
```

### 2. 配置Supabase环境变量

编辑 `.env` 文件，添加以下内容：

```env
# Supabase配置
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# JWT配置
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API配置
API_PORT=8080
DEBUG=true
```

### 3. 获取Supabase配置信息

1. 登录 [Supabase Dashboard](https://app.supabase.com)
2. 选择你的项目
3. 进入 **Settings** → **API**
4. 复制以下信息：
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_ANON_KEY`
   - **service_role secret** → `SUPABASE_SERVICE_ROLE_KEY`

### 4. 测试本地环境

```bash
# 安装依赖
pip3 install -r requirements.txt

# 启动API服务器
python3 main.py
```

如果看到 "🚀 Quest API 启动成功！" 说明配置正确。

---

## 🌐 Render部署配置

### 1. 连接GitHub仓库

1. 登录 [Render](https://render.com)
2. 点击 "New +" → "Web Service"
3. 连接你的GitHub仓库
4. 选择包含Quest API的仓库

### 2. 配置Web Service

```yaml
# 基本信息
Name: quest-api
Environment: Python 3
Region: 选择离用户最近的地区

# 构建配置
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT

# 环境变量
SUPABASE_URL: your_supabase_project_url
SUPABASE_ANON_KEY: your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY: your_supabase_service_role_key
API_PORT: 10000
NODE_ENV: production
JWT_SECRET_KEY: your-super-secret-jwt-key
SECRET_KEY: your-super-secret-key
ALLOWED_ORIGINS: https://yourdomain.com
```

### 3. 自动部署设置

- **Auto-Deploy**: 开启（代码推送时自动部署）
- **Branch**: main 或 master

## 🔧 本地测试部署

### 1. 创建本地环境变量文件

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的Supabase配置
nano .env
```

### 2. 测试本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务器
python main.py
```

### 3. 测试API端点

```bash
# 健康检查
curl http://localhost:8080/api/v1/health

# API信息
curl http://localhost:8080/api/v1/
```

## 📊 部署后验证

### 1. 检查部署状态

- Render Dashboard → 你的Web Service
- 查看 "Logs" 确认启动成功
- 检查 "Events" 中的部署历史

### 2. 测试生产API

```bash
# 替换为你的Render域名
curl https://your-app-name.onrender.com/api/v1/health
curl https://your-app-name.onrender.com/api/v1/
```

### 3. 常见问题排查

#### 问题1: 启动失败
```
ERROR: supabase_key is required
```
**解决方案**: 检查环境变量是否正确设置

#### 问题2: 端口冲突
```
ERROR: [Errno 48] Address already in use
```
**解决方案**: Render会自动分配端口，使用 `$PORT` 环境变量

#### 问题3: 依赖安装失败
```
ERROR: ModuleNotFoundError: No module named 'bs4'
```
**解决方案**: 确保 `requirements.txt` 包含所有依赖

## 🌟 生产环境优化

### 1. 性能优化

```python
# 在 main.py 中添加
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", 8080)),
        workers=1,  # Render建议使用1个worker
        log_level="info"
    )
```

### 2. 安全配置

```python
# 生产环境安全设置
ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com"
]

# 禁用调试模式
DEBUG = False
```

### 3. 监控和日志

- 启用Render的日志监控
- 设置错误告警
- 监控API响应时间

## 📱 前端集成

部署成功后，你的前端可以这样调用API：

```javascript
const API_BASE_URL = 'https://your-app-name.onrender.com/api/v1';

// 用户注册
const response = await fetch(`${API_BASE_URL}/auth/signup`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123',
    nickname: 'TestUser'
  })
});
```

## 🎯 总结

你的Quest API完全可以在Render上部署！主要优势：

✅ **完全兼容** - 使用标准Python FastAPI  
✅ **自动部署** - 代码推送自动更新  
✅ **免费套餐** - 适合开发和测试  
✅ **全球CDN** - 快速响应  
✅ **环境变量** - 安全配置管理  

按照这个指南，你的API就能成功部署到Render了！🚀
