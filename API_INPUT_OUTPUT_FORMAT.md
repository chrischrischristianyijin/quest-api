# Quest API 输入输出格式文档

## 认证相关 API

### 1. 用户注册

**端点**: `POST /api/v1/auth/register` 或 `POST /api/v1/auth/signup`

**输入格式**:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "nickname": "用户昵称",  // 可选
  "avatar_url": "https://example.com/avatar.jpg"  // 可选
}
```

**输出格式**:
```json
{
  "success": true,
  "message": "注册成功",
  "data": {
    "user_id": "884e5b3d-6016-4ff1-b5fc-23844eaac545",
    "email": "user@example.com",
    "message": "注册成功",
    "session": "eyJhbGciOiJIUzI1NiIsImtpZCI6IjJTWkh3clV5YWRXQm5EaWwiLCJ0eXAiOiJKV1QifQ..."
  }
}
```

**错误响应**:
```json
{
  "detail": "User already registered"
}
```

### 2. 用户登录

**端点**: `POST /api/v1/auth/login`

**输入格式**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**输出格式**:
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsImtpZCI6IjJTWkh3clV5YWRXQm5EaWwiLCJ0eXAiOiJKV1QifQ...",
    "token_type": "bearer",
    "user_id": "884e5b3d-6016-4ff1-b5fc-23844eaac545",
    "email": "user@example.com",
    "session": "eyJhbGciOiJIUzI1NiIsImtpZCI6IjJTWkh3clV5YWRXQm5EaWwiLCJ0eXAiOiJKV1QifQ..."
  }
}
```

**错误响应**:
```json
{
  "detail": "邮箱或密码错误"
}
```

### 3. 用户登出

**端点**: `POST /api/v1/auth/signout`

**输入格式**: 
```
Header: Authorization: Bearer <access_token>
```

**输出格式**:
```json
{
  "success": true,
  "message": "登出成功"
}
```

### 4. 检查邮箱是否存在

**端点**: `POST /api/v1/auth/check-email`

**输入格式**:
```
Query Parameter: email=user@example.com
```

**输出格式**:
```json
{
  "success": true,
  "data": {
    "exists": true
  }
}
```

### 5. 获取用户资料

**端点**: `GET /api/v1/auth/profile`

**输入格式**: 
```
Header: Authorization: Bearer <access_token>
```

**输出格式**:
```json
{
  "success": true,
  "data": {
    "id": "884e5b3d-6016-4ff1-b5fc-23844eaac545",
    "email": "user@example.com",
    "nickname": "用户昵称",
    "avatar_url": "https://example.com/avatar.jpg",
    "created_at": "2025-08-20T21:21:32.831927+00:00",
    "updated_at": "2025-08-20T21:35:40.165763+00:00"
  }
}
```

### 6. 忘记密码

**端点**: `POST /api/v1/auth/forgot-password`

**输入格式**:
```
Query Parameter: email=user@example.com
```

**输出格式**:
```json
{
  "success": true,
  "message": "重置密码邮件已发送"
}
```

## Google OAuth 相关 API

### 7. Google 登录

**端点**: `GET /api/v1/auth/google/login`

**输入格式**: 无

**输出格式**:
```json
{
  "success": true,
  "message": "Google登录",
  "data": {
    "oauth_url": "https://accounts.google.com/oauth/authorize",
    "client_id": "YOUR_GOOGLE_CLIENT_ID",
    "redirect_uri": "YOUR_REDIRECT_URI",
    "scope": "openid email profile",
    "response_type": "code"
  }
}
```

### 8. Google 回调

**端点**: `POST /api/v1/auth/google/callback`

**输入格式**:
```
Form Data: code=<authorization_code>
```

**输出格式**:
```json
{
  "success": true,
  "message": "Google登录回调功能开发中",
  "data": {
    "code": "4/0AfJohXn...",
    "note": "需要实现授权码交换access_token的逻辑"
  }
}
```

### 9. Google Token 登录

**端点**: `POST /api/v1/auth/google/token`

**输入格式**:
```
Form Data: id_token=<google_id_token>
```

**输出格式**:
```json
{
  "success": true,
  "message": "Google登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user_id": "user_id",
    "email": "user@gmail.com",
    "name": "用户姓名",
    "picture": "https://example.com/avatar.jpg",
    "auth_provider": "google"
  }
}
```

## 用户相关 API

### 10. 上传头像

**端点**: `POST /api/v1/user/upload-avatar`

**输入格式**: 
```
Header: Authorization: Bearer <access_token>
Form Data: avatar=<file>
```

**输出格式**:
```json
{
  "success": true,
  "message": "头像上传成功",
  "data": {
    "avatar_url": "https://example.com/avatar.jpg"
  }
}
```

### 11. 关注用户

**端点**: `POST /api/v1/user/follow`

**输入格式**:
```
Header: Authorization: Bearer <access_token>
{
  "follower_email": "follower@example.com",
  "following_email": "following@example.com"
}
```

**输出格式**:
```json
{
  "success": true,
  "message": "关注成功"
}
```

### 12. 获取关注状态

**端点**: `GET /api/v1/user/follow-status/{email}`

**输入格式**: 
```
Header: Authorization: Bearer <access_token>
Path Parameter: email=user@example.com
```

**输出格式**:
```json
{
  "success": true,
  "data": {
    "is_following": true,
    "follower_count": 5,
    "following_count": 3
  }
}
```

## 见解相关 API

### 13. 创建见解

**端点**: `POST /api/v1/insights`

**输入格式**:
```
Header: Authorization: Bearer <access_token>
{
  "title": "见解标题",
  "description": "见解描述",
  "image_url": "https://example.com/image.jpg",  // 可选
  "tags": ["标签1", "标签2"]  // 可选
}
```

**输出格式**:
```json
{
  "success": true,
  "message": "见解创建成功",
  "data": {
    "id": "insight_id",
    "title": "见解标题",
    "description": "见解描述",
    "image_url": "https://example.com/image.jpg",
    "tags": ["标签1", "标签2"],
    "user_id": "user_id",
    "created_at": "2025-08-20T21:21:32.831927+00:00"
  }
}
```

### 14. 获取见解列表

**端点**: `GET /api/v1/insights`

**输入格式**: 
```
Query Parameters: 
- page: 1 (默认)
- limit: 10 (默认)
- user_id: user_id (可选，筛选特定用户的见解)
```

**输出格式**:
```json
{
  "success": true,
  "data": {
    "insights": [
      {
        "id": "insight_id",
        "title": "见解标题",
        "description": "见解描述",
        "image_url": "https://example.com/image.jpg",
        "tags": ["标签1", "标签2"],
        "user_id": "user_id",
        "created_at": "2025-08-20T21:21:32.831927+00:00"
      }
    ],
    "total": 25,
    "page": 1,
    "limit": 10,
    "pages": 3
  }
}
```

## 用户标签相关 API

### 15. 创建用户标签

**端点**: `POST /api/v1/user-tags`

**输入格式**:
```
Header: Authorization: Bearer <access_token>
{
  "name": "标签名称",
  "color": "#FF5733",  // 可选
  "description": "标签描述"  // 可选
}
```

**输出格式**:
```json
{
  "success": true,
  "message": "标签创建成功",
  "data": {
    "id": "tag_id",
    "name": "标签名称",
    "color": "#FF5733",
    "description": "标签描述",
    "user_id": "user_id",
    "created_at": "2025-08-20T21:21:32.831927+00:00"
  }
}
```

### 16. 获取用户标签列表

**端点**: `GET /api/v1/user-tags`

**输入格式**: 
```
Header: Authorization: Bearer <access_token>
```

**输出格式**:
```json
{
  "success": true,
  "data": [
    {
      "id": "tag_id",
      "name": "标签名称",
      "color": "#FF5733",
      "description": "标签描述",
      "user_id": "user_id",
      "created_at": "2025-08-20T21:21:32.831927+00:00"
    }
  ]
}
```

## 元数据 API

### 17. 健康检查

**端点**: `GET /api/v1/health`

**输入格式**: 无

**输出格式**:
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "environment": "development",
  "version": "1.0.0"
}
```

### 18. API 信息

**端点**: `GET /api/v1/`

**输入格式**: 无

**输出格式**:
```json
{
  "message": "Welcome to Quest API",
  "version": "1.0.0",
  "docs": "/api/v1/docs"
}
```

## 通用响应格式

### 成功响应
所有成功的API调用都遵循以下格式：
```json
{
  "success": true,
  "message": "操作成功描述",  // 可选
  "data": { ... }  // 可选，具体数据
}
```

### 错误响应
所有错误的API调用都遵循以下格式：
```json
{
  "detail": "错误描述"
}
```

## HTTP 状态码

- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未授权（需要登录）
- `403 Forbidden`: 禁止访问
- `404 Not Found`: 资源不存在
- `422 Unprocessable Entity`: 请求格式正确但语义错误
- `500 Internal Server Error`: 服务器内部错误

## 认证方式

除了健康检查和API信息端点外，所有需要认证的端点都使用Bearer Token认证：

```
Header: Authorization: Bearer <access_token>
```

其中 `<access_token>` 是通过登录API获取的访问令牌。
