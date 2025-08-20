# 🔗 Quest API 表关联指南

## 🎯 目标

将您现有的 `users` 表与 Supabase Auth 的 `auth.users` 表建立关联，实现数据迁移和用户认证的统一。

## 🔍 当前状况

### 📋 **您现有的表**
- `users` - 包含用户基本信息和密码哈希
- `insights` - 用户见解
- `user_tags` - 用户标签

### 📋 **Supabase Auth表**
- `auth.users` - 系统管理的用户认证表
- 包含：id, email, encrypted_password, created_at等

## 🚀 关联策略

### **方案1: 创建关联表 (推荐)**

```sql
-- 创建用户关联表
CREATE TABLE user_auth_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    old_user_id UUID,           -- 您旧users表的ID
    auth_user_id UUID,          -- Supabase Auth的ID
    email TEXT,                 -- 用户邮箱
    link_type TEXT DEFAULT 'manual', -- 关联类型
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### **方案2: 直接添加字段**

```sql
-- 在现有users表中添加auth_user_id字段
ALTER TABLE users ADD COLUMN auth_user_id UUID;
```

## 🔧 关联步骤

### **步骤1: 运行关联脚本**
```bash
python3 link_existing_users.py
```

这个脚本会：
- 检查现有表结构
- 创建关联表
- 通过邮箱匹配用户
- 生成迁移SQL

### **步骤2: 手动创建Supabase Auth用户**
对于关联失败的用户，在Supabase控制台：
1. 进入 Authentication → Users
2. 点击 "Add User"
3. 输入邮箱和临时密码

### **步骤3: 执行数据迁移**
使用生成的SQL语句：
```sql
-- 创建user_profiles表
CREATE TABLE user_profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    nickname TEXT,
    avatar_url TEXT,
    bio TEXT,
    auth_provider TEXT DEFAULT 'email',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 插入用户资料数据
INSERT INTO user_profiles (id, nickname, avatar_url, bio, auth_provider, created_at, updated_at)
SELECT 
    ual.auth_user_id,
    u.nickname,
    u.avatar_url,
    u.bio,
    'email',
    u.created_at,
    u.updated_at
FROM users u
JOIN user_auth_links ual ON u.id = ual.old_user_id;
```

### **步骤4: 更新业务表外键**
```sql
-- 更新insights表的user_id
UPDATE insights SET user_id = ual.auth_user_id
FROM user_auth_links ual
WHERE insights.user_id = ual.old_user_id;

-- 更新user_tags表的user_id
UPDATE user_tags SET user_id = ual.auth_user_id
FROM user_auth_links ual
WHERE user_tags.user_id = ual.old_user_id;
```

## 🗄️ 最终表结构

### **认证相关**
- `auth.users` - Supabase管理，包含认证信息
- `user_profiles` - 用户资料，引用auth.users(id)

### **业务相关**
- `insights` - 用户见解，引用auth.users(id)
- `user_tags` - 用户标签，引用auth.users(id)

### **关联表**
- `user_auth_links` - 新旧用户ID的映射关系

## 🧪 测试验证

### **1. 检查关联结果**
```sql
-- 检查关联表
SELECT * FROM user_auth_links;

-- 检查用户资料
SELECT * FROM user_profiles;

-- 检查业务表外键
SELECT i.id, i.title, up.nickname 
FROM insights i 
JOIN user_profiles up ON i.user_id = up.id;
```

### **2. 测试用户登录**
```bash
# 使用Supabase Auth登录
curl -X POST http://localhost:3001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"existing_user@example.com","password":"temp_password"}'
```

### **3. 测试业务功能**
- 获取用户见解
- 管理用户标签
- 更新用户资料

## 🚨 注意事项

### **数据安全**
- 迁移前务必备份所有表
- 测试环境先验证
- 分批处理大量数据

### **用户通知**
- 通知用户密码已重置
- 提供新的登录方式说明
- 处理用户反馈

### **回滚准备**
- 保留旧表结构
- 准备回滚脚本
- 监控系统状态

## 🔄 迁移后清理

### **可选步骤**
```sql
-- 删除关联表（确认迁移成功后）
-- DROP TABLE user_auth_links;

-- 重命名旧users表（确认迁移成功后）
-- ALTER TABLE users RENAME TO users_old;
```

### **代码更新**
- 移除对旧users表的引用
- 使用新的表结构
- 更新API文档

## 🎉 完成标志

- ✅ 所有用户都能通过Supabase Auth登录
- ✅ 用户资料完整保留
- ✅ 业务功能正常运行
- ✅ 外键关系正确建立
- ✅ 数据完整性验证通过

## 📞 需要帮助？

如果关联过程中遇到问题：
1. 检查关联脚本日志
2. 验证Supabase配置
3. 确认表结构正确
4. 测试各个功能端点

---

**记住：表关联是重要操作，请按步骤谨慎执行！** 🛡️
