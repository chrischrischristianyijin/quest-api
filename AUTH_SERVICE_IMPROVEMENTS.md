# AuthService 改进说明

## 🚀 主要改进

### 1. **增强的日志记录**
- 使用结构化日志格式
- 详细的成功/失败状态记录
- 使用表情符号提高日志可读性
- 统一的日志级别管理

### 2. **改进的异常处理**
- 区分 Supabase 特定异常和通用异常
- 更好的错误消息和状态码
- 统一的异常处理模式

### 3. **唯一用户名生成**
- 基于邮箱自动生成用户名
- 清理特殊字符，确保用户名有效性
- 使用 UUID 后缀保证唯一性

### 4. **数据库触发器支持**
- 自动创建用户资料
- 自动添加默认标签
- 自动更新时间戳
- 软删除支持

## 📋 使用方法

### 基本注册流程

```python
from app.services.auth_service import AuthService
from app.models.user import UserCreate

# 创建服务实例
auth_service = AuthService()

# 注册用户
user_data = UserCreate(
    email="user@example.com",
    password="securepassword123",
    nickname="johndoe"
)

try:
    result = await auth_service.register_user(user_data)
    print(f"注册成功: {result}")
except ValueError as e:
    print(f"注册失败: {e}")
```

### 登录流程

```python
from app.models.user import UserLogin

# 用户登录
login_data = UserLogin(
    email="user@example.com",
    password="securepassword123"
)

try:
    result = await auth_service.login_user(login_data)
    access_token = result["access_token"]
    print(f"登录成功，令牌: {access_token}")
except ValueError as e:
    print(f"登录失败: {e}")
```

### 检查邮箱可用性

```python
# 检查邮箱是否可用
try:
    result = await auth_service.check_email("user@example.com")
    if result["available"]:
        print("邮箱可用")
    else:
        print("邮箱已被使用")
except ValueError as e:
    print(f"检查失败: {e}")
```

## 🗄️ 数据库触发器

### 自动创建用户资料

当用户在 `auth.users` 表中创建时，触发器会自动：
1. 生成唯一用户名
2. 在 `profiles` 表中创建用户资料
3. 在 `user_tags` 表中添加默认标签

### 运行触发器

```sql
-- 在 Supabase SQL 编辑器中运行
\i database_triggers.sql
```

### 触发器功能

- **`create_profile_for_new_user`**: 自动创建用户资料
- **`create_default_tags_for_new_user`**: 自动添加默认标签
- **`update_profile_timestamp`**: 自动更新时间戳
- **`soft_delete_insight`**: 实现软删除

## 🔧 配置要求

### 环境变量

```env
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_REDIRECT_URI=your_redirect_uri
```

### 数据库表结构

确保以下表存在：
- `auth.users` (Supabase Auth)
- `public.profiles`
- `public.user_tags`
- `public.insights`

## 📊 日志示例

### 成功注册
```
2024-01-15 10:30:00 - app.services.auth_service - INFO - 开始注册用户: user@example.com
2024-01-15 10:30:01 - app.services.auth_service - INFO - 生成用户名: user_abc12345 (基于邮箱: user@example.com)
2024-01-15 10:30:02 - app.services.auth_service - INFO - ✅ Supabase Auth用户创建成功: 550e8400-e29b-41d4-a716-446655440000
2024-01-15 10:30:03 - app.services.auth_service - INFO - ✅ 用户资料创建成功: user@example.com
2024-01-15 10:30:04 - app.services.auth_service - INFO - 🎉 用户注册完成: user@example.com
```

### 注册失败
```
2024-01-15 10:30:00 - app.services.auth_service - INFO - 开始注册用户: existing@example.com
2024-01-15 10:30:01 - app.services.auth_service - INFO - 邮箱已存在于auth.users: existing@example.com
2024-01-15 10:30:01 - app.services.auth_service - ERROR - 注册验证失败: 邮箱已被注册
```

## 🚨 错误处理

### 常见错误类型

1. **SupabaseException**: Supabase 服务错误
2. **ValueError**: 业务逻辑错误（如邮箱已存在）
3. **Exception**: 未知错误

### 错误响应格式

```json
{
  "success": false,
  "detail": "具体错误信息"
}
```

## 🔄 回滚机制

如果用户资料创建失败，系统会自动：
1. 删除已创建的 Supabase Auth 用户
2. 记录回滚操作日志
3. 返回详细的错误信息

## 📈 性能优化

### 数据库索引
- 邮箱和用户名唯一索引
- 用户ID外键索引
- 全文搜索索引

### 批量操作
- 默认标签批量插入
- 使用 `ON CONFLICT` 避免重复插入

## 🔐 安全特性

- 密码哈希存储（Supabase Auth）
- 服务角色密钥用于管理操作
- 输入验证和清理
- 软删除保护数据完整性

## 🧪 测试建议

1. **单元测试**: 测试各个方法的逻辑
2. **集成测试**: 测试与 Supabase 的交互
3. **错误测试**: 测试各种异常情况
4. **性能测试**: 测试大量用户注册的性能

## 📚 相关文档

- [Supabase Auth 文档](https://supabase.com/docs/guides/auth)
- [FastAPI 异常处理](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [PostgreSQL 触发器](https://www.postgresql.org/docs/current/triggers.html)
