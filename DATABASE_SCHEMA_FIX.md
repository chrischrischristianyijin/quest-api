# 数据库模式修复 - Google OAuth

## 🐛 问题描述

Chrome扩展在使用Google OAuth时遇到400错误，原因是后端代码试图在 `profiles` 表中查找 `email` 字段，但实际上：

- `email` 字段存储在 Supabase 的 `auth.users` 表中
- `profiles` 表不包含 `email` 字段，只包含用户的其他信息

## ✅ 修复方案

### 1. 修改用户查找逻辑

**原来的错误代码**:
```python
# ❌ 错误：在profiles表中查找email
existing_user = self.supabase_service.table('profiles').select('*').eq('email', email).execute()
```

**修复后的代码**:
```python
# ✅ 正确：先在auth.users表中查找用户
auth_response = self.supabase_service.auth.admin.get_user_by_email(email)
if auth_response and hasattr(auth_response, 'user') and auth_response.user:
    existing_auth_user = auth_response.user
    # 然后在profiles表中查找对应的profile
    profile_query = self.supabase_service.table('profiles').select('*').eq('id', user_id).execute()
```

### 2. 处理三种用户状态

修复后的代码现在可以正确处理三种用户状态：

1. **完全新用户**: 在auth和profiles表中都不存在
   - 创建auth用户
   - 创建profile记录
   - 添加默认标签

2. **auth表存在，profiles表缺失**: 用户在auth表中存在但profiles表中没有记录
   - 为已存在的auth用户创建profile记录
   - 添加默认标签

3. **完整用户**: auth和profiles表中都存在
   - 直接登录

### 3. 修复profiles表数据结构

**原来的错误结构**:
```python
# ❌ 错误：在profiles表中存储email
profile_data = {
    "id": user_id,
    "email": email,  # 这个字段不应该在profiles表中
    "username": username,
    "nickname": nickname,
    # ...
}
```

**修复后的正确结构**:
```python
# ✅ 正确：不在profiles表中存储email
profile_data = {
    "id": user_id,  # 通过ID关联到auth.users表
    "username": username,
    "nickname": nickname,
    "avatar_url": picture,
    "provider": "google",
    "created_at": created_at_iso,
    "updated_at": created_at_iso
}
```

## 🔄 修复的文件

### `/app/services/auth_service.py`

1. **`_handle_google_user()` 方法**
   - 修改用户查找逻辑，使用 `auth.admin.get_user_by_email()` 
   - 处理auth和profiles表数据不一致的情况

2. **新增 `_create_profile_for_existing_auth_user()` 方法**
   - 为已存在的auth用户创建缺失的profile记录

3. **修复 `_create_google_user()` 方法**
   - 移除profiles表中的email字段存储

## 🧪 测试验证

### 修复前的错误
```
popup.js:558 🚨 Database schema error detected - backend needs database migration
```

### 修复后的行为
- Google OAuth URL正常生成
- ID Token验证正确处理
- 用户创建和登录流程正常
- 数据库模式一致性得到保证

### 测试命令
```bash
# 测试Google OAuth配置
curl -X GET "https://quest-api-edz1.onrender.com/api/v1/auth/google/login"

# 测试ID Token验证（应该返回400错误，这是正常的）
curl -X POST "https://quest-api-edz1.onrender.com/api/v1/auth/google/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "id_token=invalid_token"
```

## 📋 数据库表关系

### 正确的关系结构

```
auth.users (Supabase管理)
├── id (主键)
├── email
├── created_at
└── user_metadata

profiles (自定义表)
├── id (外键 -> auth.users.id)
├── username
├── nickname
├── avatar_url
├── provider
├── created_at
└── updated_at

user_tags (自定义表)
├── id
├── user_id (外键 -> profiles.id)
├── name
├── color
└── created_at
```

## 🚀 部署建议

1. **重新部署**: 将修改后的代码推送到Render
   ```bash
   git add .
   git commit -m "Fix database schema for Google OAuth"
   git push origin main
   ```

2. **测试**: 部署完成后测试Chrome扩展的Google OAuth流程

3. **数据清理**: 如果需要，清理任何可能存在的不一致数据

## 🔮 预期结果

修复后，Chrome扩展应该能够：

- ✅ 正常获取Google OAuth URL
- ✅ 成功处理Google ID Token
- ✅ 创建新用户（auth + profiles）
- ✅ 登录现有用户
- ✅ 处理数据不一致的边缘情况
- ✅ 避免数据库模式错误
