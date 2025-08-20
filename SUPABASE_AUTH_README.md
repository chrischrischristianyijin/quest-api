# 🚀 Quest API - Supabase Auth 使用指南

## 🎯 简化后的架构

现在您的Quest API完全使用 **Supabase Auth** 来处理用户认证，不再需要复杂的密码加密逻辑！

## ✅ 优势

### 1. **更简单**
- 不需要处理密码加密/验证
- 不需要管理密码哈希
- 自动处理密码重置

### 2. **更安全**
- Supabase使用行业标准的bcrypt加密
- 自动处理密码强度验证
- 内置安全最佳实践

### 3. **更强大**
- 内置邮箱验证
- 自动密码重置
- 支持多种认证方式

## 🔧 当前功能

### ✅ **已实现**
- 用户注册 (`/api/v1/auth/register`)
- 用户登录 (`/api/v1/auth/login`)
- 用户登出 (`/api/v1/auth/signout`)
- 获取用户资料 (`/api/v1/auth/profile`)
- 检查邮箱存在 (`/api/v1/auth/check-email`)
- 忘记密码 (`/api/v1/auth/forgot-password`)
- Google登录端点 (`/api/v1/auth/google/login`)

### 🚧 **开发中**
- Google OAuth完整实现
- 密码重置流程

## 🚀 使用方法

### 1. **用户注册**
```bash
curl -X POST http://localhost:3001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "nickname": "用户名"
  }'
```

### 2. **用户登录**
```bash
curl -X POST http://localhost:3001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### 3. **使用JWT Token**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:3001/api/v1/auth/profile
```

## 🗄️ 数据库结构

### ⚠️ **重要：使用Supabase自带的表！**

#### 1. **`auth.users` (系统自带，不要修改)**
```sql
-- 这是Supabase自动管理的表，包含：
- id (UUID) - 用户唯一标识
- email - 用户邮箱
- encrypted_password - 加密后的密码
- email_confirmed_at - 邮箱确认时间
- created_at - 创建时间
- updated_at - 更新时间
- last_sign_in_at - 最后登录时间
-- 等等...
```

#### 2. **我们只需要创建业务表**
```sql
-- 用户资料表（可选）
CREATE TABLE user_profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    nickname TEXT,
    avatar_url TEXT,
    bio TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 见解表
CREATE TABLE insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 用户标签表
CREATE TABLE user_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    name TEXT NOT NULL,
    color TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🔐 认证流程

### 1. **注册流程**
```
用户输入邮箱密码 → Supabase Auth创建账户 → 用户自动存储在auth.users表 → 返回成功
```

### 2. **登录流程**
```
用户输入邮箱密码 → Supabase Auth验证 → 创建JWT Token → 返回Token
```

### 3. **API调用**
```
请求头包含JWT Token → 验证Token → 从auth.users表获取用户信息 → 执行业务逻辑
```

## 🧪 测试建议

### 1. **重启服务器**
```bash
python3 main.py
```

### 2. **测试注册**
```bash
curl -X POST http://localhost:3001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","nickname":"测试用户"}'
```

### 3. **测试登录**
```bash
curl -X POST http://localhost:3001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

## 🚨 注意事项

### 1. **环境变量**
确保 `.env` 文件包含：
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
JWT_SECRET_KEY=your_jwt_secret
```

### 2. **Supabase设置**
- 在Supabase控制台启用邮箱认证
- 配置邮箱模板（可选）
- 设置密码策略（可选）

### 3. **生产环境**
- 更改JWT密钥
- 配置CORS域名
- 设置密码强度要求

### 4. **数据库权限**
- `auth.users` 表由Supabase自动管理
- 业务表需要设置适当的RLS策略
- 使用 `REFERENCES auth.users(id)` 建立外键关系

## 🎉 总结

现在您的Quest API：
- ✅ 使用Supabase Auth处理认证
- ✅ 不需要复杂的密码加密逻辑
- ✅ 不需要自定义users表
- ✅ 更安全、更简单、更强大
- ✅ 支持所有基本认证功能

**下一步**: 可以专注于实现Google OAuth或其他高级功能！🚀

---

**需要帮助？** 查看API文档: `http://localhost:3001/api/v1/docs`
