# 🔐 Quest API - 混合认证系统指南

## 🎯 系统架构

您的Quest API现在支持**双重认证方式**：

### ✅ **认证方式**
1. **Supabase Auth** - 传统邮箱密码登录
2. **Google OAuth** - 第三方登录

### 🌟 **架构优势**
- 用户可以选择喜欢的登录方式
- 提高用户注册转化率
- 减少密码遗忘问题
- 更安全的第三方认证

## 🔧 当前实现状态

### ✅ **已完成**
- Supabase Auth (邮箱密码)
- Google登录端点
- Google Token验证
- 用户数据同步

### 🚧 **开发中**
- Google OAuth完整流程
- 用户账户关联
- 密码重置流程

## 🚀 API端点

### 1. **Supabase Auth**
```bash
# 用户注册
POST /api/v1/auth/register

# 用户登录
POST /api/v1/auth/login

# 用户登出
POST /api/v1/auth/signout

# 获取用户资料
GET /api/v1/auth/profile

# 检查邮箱存在
POST /api/v1/auth/check-email

# 忘记密码
POST /api/v1/auth/forgot-password
```

### 2. **Google OAuth**
```bash
# 获取OAuth URL
GET /api/v1/auth/google/login

# OAuth回调处理
POST /api/v1/auth/google/callback

# 直接Token登录
POST /api/v1/auth/google/token
```

## 🔐 认证流程

### **Supabase Auth流程**
```
用户输入邮箱密码 → Supabase验证 → 创建JWT Token → 返回Token
```

### **Google OAuth流程**
```
用户点击Google登录 → 重定向到Google → 用户授权 → 获取ID Token → 验证Token → 创建/获取用户 → 返回JWT Token
```

## 🗄️ 数据库结构

### 1. **`auth.users` (Supabase管理)**
```sql
-- 包含所有用户，无论认证方式
- id (UUID)
- email
- encrypted_password (可能为空，Google用户)
- created_at
- updated_at
```

### 2. **`user_profiles` (我们管理)**
```sql
CREATE TABLE user_profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    nickname TEXT,
    avatar_url TEXT,
    bio TEXT,
    auth_provider TEXT DEFAULT 'email', -- 'email' 或 'google'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 3. **业务表**
```sql
-- 见解表
CREATE TABLE insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
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

## 🧪 测试方法

### 1. **测试Supabase Auth**
```bash
# 注册新用户
curl -X POST http://localhost:3001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","nickname":"测试用户"}'

# 登录
curl -X POST http://localhost:3001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

### 2. **测试Google登录端点**
```bash
# 获取OAuth信息
curl http://localhost:3001/api/v1/auth/google/login

# 使用ID Token登录（需要真实的Google ID Token）
curl -X POST http://localhost:3001/api/v1/auth/google/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "id_token=YOUR_GOOGLE_ID_TOKEN"
```

## 🔧 配置要求

### 1. **环境变量**
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
JWT_SECRET_KEY=your_jwt_secret
```

### 2. **Google OAuth配置**
```bash
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=your_redirect_uri
```

## 🚨 注意事项

### 1. **用户数据一致性**
- 同一邮箱的用户应该关联到同一账户
- 支持用户绑定多个认证方式
- 处理用户资料合并

### 2. **安全性**
- Google ID Token验证
- JWT Token过期管理
- 用户权限控制

### 3. **用户体验**
- 统一的用户资料
- 无缝的认证切换
- 密码重置支持

## 🎉 系统优势

### ✅ **对用户**
- 多种登录选择
- 无需记住密码
- 快速注册登录

### ✅ **对开发者**
- 统一的API接口
- 简化的用户管理
- 安全的认证流程

### ✅ **对系统**
- 高可用性
- 易于扩展
- 标准化的架构

## 🚀 下一步开发

### 1. **完善Google OAuth**
- 实现完整的OAuth流程
- 处理授权码交换
- 用户账户关联

### 2. **增强用户体验**
- 账户绑定功能
- 统一登录界面
- 密码重置流程

### 3. **扩展认证方式**
- GitHub OAuth
- Facebook OAuth
- 手机号登录

---

**现在您的Quest API支持双重认证，用户体验更佳！** 🎊
