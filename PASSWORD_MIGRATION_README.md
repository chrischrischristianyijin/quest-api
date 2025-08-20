# 🔐 Quest API 密码迁移指南

## 📋 问题描述

您的Quest API现在遇到了两个主要问题：

1. **密码加密问题**: 原本的密码是bcrypt加密的（如：`$2b$10$lp.hYO1sVTvXuiPP/XwJ2.V5H5bweyeCAMZ1A1Zd6H9h0/narcccW`），但现在API无法验证这些密码
2. **Google登录缺失**: 前端在请求Google登录端点，但API没有实现
3. **CORS问题**: OPTIONS预检请求返回400错误

## ✅ 已修复的问题

### 1. **密码验证支持**
- ✅ 修改了 `app/services/auth_service.py`，现在支持两种登录方式：
  - Supabase Auth（新用户）
  - bcrypt密码验证（已有用户）
- ✅ 添加了 `get_user_by_email()` 方法来获取用户信息
- ✅ 登录时会先尝试Supabase Auth，失败后尝试bcrypt验证

### 2. **Google登录端点**
- ✅ 添加了 `/api/v1/auth/google/login` 端点
- ✅ 添加了 `/api/v1/auth/google/callback` 端点
- ⚠️ 目前返回占位符数据，需要进一步实现Google OAuth逻辑

### 3. **CORS配置修复**
- ✅ 修复了CORS中间件配置
- ✅ 现在支持OPTIONS预检请求
- ✅ 允许所有必要的HTTP方法和头部

## 🚀 解决步骤

### 步骤1: 重启API服务器
```bash
# 停止当前服务器 (Ctrl+C)
# 重新启动
python3 main.py
```

### 步骤2: 检查数据库结构
在Supabase控制台中，确保 `users` 表有 `password_hash` 字段：

```sql
-- 如果需要添加password_hash字段
ALTER TABLE users ADD COLUMN password_hash TEXT;
```

### 步骤3: 运行密码迁移脚本
```bash
python3 migrate_bcrypt_passwords.py
```

这个脚本会：
- 检查数据库结构
- 识别已有的bcrypt密码
- 确保密码哈希字段正确设置

### 步骤4: 测试修复
```bash
# 测试健康检查
curl http://localhost:3001/api/v1/health

# 测试Google登录端点
curl http://localhost:3001/api/v1/auth/google/login

# 测试CORS预检请求
curl -X OPTIONS http://localhost:3001/api/v1/auth/login \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type"
```

## 🔍 技术细节

### 密码验证流程
```python
# 1. 尝试Supabase Auth登录
try:
    response = supabase.auth.sign_in_with_password(...)
    # 成功则返回JWT令牌
except:
    # 2. 失败则尝试bcrypt验证
    user_data = get_user_by_email(email)
    if verify_password(password, user_data.password_hash):
        # 成功则创建JWT令牌
```

### CORS配置
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=[
        "Accept", "Content-Type", "Authorization", 
        "X-Requested-With", "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
    ],
    max_age=86400,  # 预检请求缓存24小时
)
```

## 🧪 测试建议

### 1. **测试已有用户登录**
使用您提到的bcrypt密码测试登录功能

### 2. **测试CORS**
从不同域名（如 `http://localhost:3000`）发送请求

### 3. **测试Google登录端点**
访问 `http://localhost:3001/api/v1/auth/google/login`

## 🚨 注意事项

1. **生产环境**: 不要使用 `allow_origins=["*"]`，应该限制具体域名
2. **Google OAuth**: 需要进一步实现Google登录逻辑
3. **密码安全**: 确保 `password_hash` 字段在数据库中有适当的权限设置

## 🔧 故障排除

### 如果仍有CORS问题
检查浏览器控制台，确保：
- 预检请求返回200状态
- 响应头包含正确的CORS信息

### 如果密码验证失败
检查：
- 数据库中的 `password_hash` 字段是否正确设置
- bcrypt密码格式是否正确（以 `$2b$` 或 `$2a$` 开头）

### 如果Google登录返回404
确保：
- 重启了API服务器
- 路由正确注册
- 没有语法错误

## 📞 需要帮助？

如果问题仍然存在，请：
1. 检查API服务器日志
2. 确认数据库结构
3. 测试各个端点
4. 查看浏览器网络请求

---

**修复完成后，您的Quest API应该能够：**
- ✅ 验证已有的bcrypt密码
- ✅ 处理Google登录请求
- ✅ 正确处理CORS预检请求
- ✅ 支持所有认证功能
