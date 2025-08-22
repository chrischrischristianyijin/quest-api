# 🌍 环境变量设置指南

## ❌ 当前问题
你的应用显示 "Supabase未初始化" 错误，这是因为缺少必需的环境变量配置。

## 🔧 解决方案

### 🚀 Render平台配置（推荐）

#### 步骤1: 登录Render控制台
1. 访问 [https://dashboard.render.com](https://dashboard.render.com)
2. 登录你的账户

#### 步骤2: 选择Web Service
1. 在仪表板中找到你的Quest API服务
2. 点击进入服务详情页面

#### 步骤3: 配置环境变量
1. 点击左侧菜单的 **Environment** 标签
2. 在 **Environment Variables** 部分添加以下变量：

```env
# 必需的环境变量
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# 可选的环境变量
API_PORT=8080
NODE_ENV=production
JWT_SECRET_KEY=your-secret-key-change-in-production
SECRET_KEY=your-secret-key-change-in-production
```

#### 步骤4: 保存并重新部署
1. 点击 **Save Changes** 按钮
2. 等待服务自动重新部署
3. 检查部署日志确认成功

### 📱 获取Supabase配置值

#### 步骤1: 登录Supabase
1. 访问 [https://supabase.com](https://supabase.com)
2. 登录你的账户

#### 步骤2: 选择项目
1. 在仪表板中选择你的项目
2. 如果没有项目，创建一个新项目

#### 步骤3: 获取配置
1. 在项目仪表板中，点击左侧菜单的 **Settings** → **API**
2. 复制以下值：
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_ANON_KEY`
   - **service_role secret** → `SUPABASE_SERVICE_ROLE_KEY`

### 4. 示例配置
```env
# 示例（请替换为你的实际值）
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYzNjU2NzIwMCwiZXhwIjoxOTUyMTQzMjAwfQ.example
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoic2VydmljZV9yb2xlIiwiaWF0IjoxNjM2NTY3MjAwLCJleHAiOjE5NTIxNDMyMDB9.example
```

## 🔍 验证配置

### 方法1: 使用检查脚本
```bash
# 检查Render环境变量
python check_render_env.py

# 检查本地环境变量
python check_env.py
```

### 方法2: 查看应用日志
启动后，你应该看到：
```
🚀 Starting Quest API...
🔍 检查环境变量配置...
✅ SUPABASE_URL: 已设置
✅ SUPABASE_ANON_KEY: 已设置
✅ SUPABASE_SERVICE_ROLE_KEY: 已设置
✅ 环境变量配置检查通过
🔧 初始化Supabase连接...
🔗 连接到Supabase: https://abcdefghijklmnop.supabase.co...
✅ Supabase Auth连接测试成功
✅ profiles表检查通过
✅ insights表检查通过
✅ 数据库表结构检查完成
✅ Supabase连接初始化成功
✅ Quest API started successfully
```

## 🚀 启动应用

### Render平台（自动）
- 环境变量配置完成后，Render会自动重新部署
- 无需手动启动

### 本地开发
```bash
# 直接运行
python main.py

# 使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

## 🔍 故障排除

### 问题1: 环境变量未生效
- 确保在Render平台点击了 **Save Changes**
- 等待服务重新部署完成
- 检查部署日志确认成功

### 问题2: 权限错误
- 确保 `SUPABASE_ANON_KEY` 是公开的anon key
- 确保 `SUPABASE_SERVICE_ROLE_KEY` 是私有的service role key

### 问题3: 网络连接问题
- 检查防火墙设置
- 确保可以访问 `https://supabase.com`

### 问题4: 环境变量名称错误
- 确保名称完全正确（区分大小写）
- 不要有多余的空格或特殊字符

## 📝 注意事项

1. **环境变量名称**
   - 必须完全匹配：`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
   - 区分大小写

2. **安全建议**
   - 定期轮换API密钥
   - 使用最小权限原则
   - 监控API使用情况

3. **Render特定配置**
   - 环境变量修改后需要重新部署
   - 部署过程可能需要几分钟
   - 检查部署日志确认成功

## 🆘 获取帮助

如果仍然遇到问题：
1. 检查Render部署日志
2. 运行 `python check_render_env.py` 检查配置
3. 确认环境变量名称和值正确
4. 检查Supabase项目状态

## 🔧 快速修复步骤

1. **立即检查**：
   ```bash
   python check_render_env.py
   ```

2. **Render平台操作**：
   - 登录 [Render Dashboard](https://dashboard.render.com)
   - 选择你的Web Service
   - 点击 Environment 标签
   - 添加/修改环境变量
   - 保存并等待重新部署

3. **验证修复**：
   - 检查部署日志
   - 测试API端点
   - 查看应用启动日志

---

**记住**: 在Render平台上，环境变量配置完成后需要重新部署服务才能生效！ 🚀
