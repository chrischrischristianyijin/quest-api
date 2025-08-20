# 🔄 Quest API 用户数据迁移指南

## 🎯 迁移目标

将您现有的 `users` 表中的用户数据迁移到新的 Supabase Auth 架构，**保留所有重要数据**！

## 📋 迁移策略

### ✅ **保留的数据**
- 用户基本信息（邮箱、昵称、头像等）
- 用户创建时间
- 用户相关设置

### 🔄 **迁移的数据**
- 从 `users` 表 → `user_profiles` 表
- 从自定义认证 → Supabase Auth

### ❌ **不需要的数据**
- 密码哈希（由Supabase Auth管理）
- 认证相关字段

## 🚀 迁移步骤

### 步骤1: **备份现有数据**
```bash
# 在Supabase控制台导出users表数据
# 或者使用SQL备份
SELECT * FROM users;
```

### 步骤2: **运行迁移脚本**
```bash
python3 migrate_existing_users.py
```

### 步骤3: **手动创建Supabase Auth用户**
对于迁移失败的用户，需要在Supabase控制台手动创建：
1. 进入 Authentication → Users
2. 点击 "Add User"
3. 输入邮箱和临时密码
4. 用户首次登录时修改密码

### 步骤4: **验证迁移结果**
```bash
# 测试用户登录
curl -X POST http://localhost:3001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"existing_user@example.com","password":"temp_password"}'
```

## 🗄️ 新表结构

### 1. **`auth.users` (Supabase管理)**
```sql
-- 包含：id, email, encrypted_password, created_at等
-- 我们不需要也不应该修改这个表
```

### 2. **`user_profiles` (我们管理)**
```sql
CREATE TABLE user_profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    nickname TEXT,
    avatar_url TEXT,
    bio TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 3. **业务表保持不变**
```sql
-- insights, user_tags等表继续使用
-- 只需要更新外键引用到auth.users(id)
```

## 🔧 迁移脚本功能

### ✅ **自动处理**
- 检查现有users表
- 创建user_profiles表
- 迁移用户资料数据
- 生成迁移报告

### ⚠️ **需要手动处理**
- 在Supabase Auth中创建用户账户
- 设置用户密码
- 处理特殊字段映射

## 🧪 测试迁移

### 1. **检查数据完整性**
```sql
-- 在Supabase控制台执行
SELECT COUNT(*) FROM user_profiles;
SELECT * FROM user_profiles LIMIT 5;
```

### 2. **测试用户登录**
```bash
# 使用迁移后的用户测试登录
curl -X POST http://localhost:3001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'
```

### 3. **测试业务功能**
- 获取用户资料
- 创建见解
- 管理标签

## 🚨 注意事项

### 1. **数据安全**
- 迁移前务必备份
- 测试环境先验证
- 分批迁移大量数据

### 2. **用户通知**
- 通知用户密码已重置
- 提供密码重置链接
- 说明新的登录方式

### 3. **回滚计划**
- 保留旧表结构
- 准备回滚脚本
- 监控系统运行状态

## 🔄 迁移后清理

### 1. **验证所有功能正常**
- 用户认证
- 业务逻辑
- 数据完整性

### 2. **删除旧表（可选）**
```sql
-- 确认迁移成功后，可以删除旧表
-- DROP TABLE users;
```

### 3. **更新应用代码**
- 移除对旧users表的引用
- 使用新的表结构
- 更新API文档

## 🎉 迁移完成标志

- ✅ 所有用户都能正常登录
- ✅ 用户资料完整保留
- ✅ 业务功能正常运行
- ✅ 新用户注册正常
- ✅ 旧用户数据完整

## 📞 需要帮助？

如果迁移过程中遇到问题：
1. 检查迁移脚本日志
2. 验证Supabase配置
3. 确认数据表结构
4. 测试各个功能端点

---

**记住：数据迁移是重要操作，请谨慎处理！** 🛡️
