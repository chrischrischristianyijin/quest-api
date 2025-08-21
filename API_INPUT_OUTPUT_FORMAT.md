# Quest API 完整接口文档

## 🔐 认证系统接口

### 用户注册
```http
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123",
  "nickname": "johndoe"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "用户注册成功",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "nickname": "johndoe",
      "created_at": "2024-01-15T10:30:00Z"
    },
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

### 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "session": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

### 获取用户资料
```http
GET /api/v1/auth/profile
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "nickname": "johndoe",
    "avatar_url": "https://example.com/avatar.jpg",
    "bio": "这是我的个人简介",
    "followers_count": 0,
    "following_count": 0,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 检查邮箱
```http
POST /api/v1/auth/check-email
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "exists": false,
    "available": true
  }
}
```

### 忘记密码
```http
POST /api/v1/auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "密码重置邮件已发送"
}
```

### 用户登出
```http
POST /api/v1/auth/signout
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "success": true,
  "message": "登出成功"
}
```

## 🌐 网页元数据提取接口

### 提取单个网页元数据
```http
POST /api/v1/metadata/extract
Content-Type: application/x-www-form-urlencoded

url=https://example.com/article
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "url": "https://example.com/article",
    "title": "示例文章标题",
    "description": "这是一篇关于人工智能的文章...",
    "image_url": "https://example.com/image.jpg",
    "site_name": "示例网站",
    "type": "article",
    "extraction_time": "2024-01-15T10:30:00Z"
  }
}
```

### 批量提取元数据
```http
POST /api/v1/metadata/batch-extract
Content-Type: application/json

{
  "urls": [
    "https://example1.com",
    "https://example2.com",
    "https://example3.com"
  ]
}
```

**响应示例：**
```json
{
  "success": true,
  "data": [
    {
      "url": "https://example1.com",
      "title": "网站1标题",
      "description": "网站1描述",
      "image_url": "https://example1.com/image.jpg",
      "status": "success"
    },
    {
      "url": "https://example2.com",
      "title": "网站2标题",
      "description": "网站2描述",
      "image_url": "https://example2.com/image.jpg",
      "status": "success"
    }
  ]
}
```

### 从URL创建insight
```http
POST /api/v1/metadata/create-insight
Authorization: Bearer {token}
Content-Type: application/json

{
  "url": "https://example.com/article",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "custom_tags": ["技术", "AI"],
  "custom_description": "这是一篇很有价值的文章"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "Insight创建成功",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://example.com/article",
    "title": "示例文章标题",
    "description": "这是一篇很有价值的文章",
    "image_url": "https://example.com/image.jpg",
    "tags": ["技术", "AI"],
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### 预览insight
```http
GET /api/v1/metadata/preview/{insight_id}
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "url": "https://example.com/article",
    "title": "示例文章标题",
    "description": "这是一篇很有价值的文章",
    "image_url": "https://example.com/image.jpg",
    "tags": ["技术", "AI"],
    "preview_url": "https://example.com/preview/660e8400-e29b-41d4-a716-446655440000"
  }
}
```

## 📚 见解管理接口

### 获取见解列表
```http
GET /api/v1/insights?page=1&limit=10&user_id=xxx&search=AI
Authorization: Bearer {token}
```

**参数说明：**
- `page`: 页码（默认1）
- `limit`: 每页数量（默认10，最大100）
- `user_id`: 用户ID筛选（可选，不传则默认当前登录用户）
- `search`: 搜索关键词（可选，在标题和描述中搜索）

**权限控制：**
- 如果指定`user_id`，只能查看自己的insights
- 如果不指定`user_id`，默认查看当前登录用户的insights

**响应示例：**
```json
{
  "success": true,
  "data": {
    "insights": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440000",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "url": "https://example.com/article",
        "title": "AI技术发展趋势",
        "description": "关于人工智能的最新发展...",
        "image_url": "https://example.com/image.jpg",
        "tags": ["技术", "AI"],
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 25,
      "total_pages": 3
    }
  }
}
```

### 获取见解详情
```http
GET /api/v1/insights/{insight_id}
Authorization: Bearer {token}
```

**权限控制：**
- 用户只能访问自己的insights
- 如果尝试访问其他用户的insight，返回403错误

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://example.com/article",
    "title": "AI技术发展趋势",
    "description": "关于人工智能的最新发展...",
    "image_url": "https://example.com/image.jpg",
    "tags": ["技术", "AI"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 创建新见解
```http
POST /api/v1/insights
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "我的新见解",
  "description": "这是一个关于技术的见解",
  "url": "https://example.com",
  "image_url": "https://example.com/image.jpg",
  "tags": ["技术", "编程"]
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "见解创建成功",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "我的新见解",
    "description": "这是一个关于技术的见解",
    "url": "https://example.com",
    "image_url": "https://example.com/image.jpg",
    "tags": ["技术", "编程"],
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### 更新见解
```http
PUT /api/v1/insights/{insight_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "更新后的标题",
  "description": "更新后的描述",
  "tags": ["技术", "AI", "机器学习"]
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "见解更新成功",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "title": "更新后的标题",
    "description": "更新后的描述",
    "tags": ["技术", "AI", "机器学习"],
    "updated_at": "2024-01-15T11:00:00Z"
  }
}
```

### 删除见解
```http
DELETE /api/v1/insights/{insight_id}
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "success": true,
  "message": "见解删除成功"
}
```

## 🏷️ 标签管理接口

### 获取用户标签列表
```http
GET /api/v1/user-tags?user_id=xxx&page=1&limit=10
Authorization: Bearer {token}
```

**参数说明：**
- `user_id`: 用户ID筛选（可选，不传则默认当前登录用户）
- `page`: 页码（默认1）
- `limit`: 每页数量（默认10，最大100）

**权限控制：**
- 如果指定`user_id`，只能查看自己的标签
- 如果不指定`user_id`，默认查看当前登录用户的标签

**响应示例：**
```json
{
  "success": true,
  "data": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440000",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "人工智能",
      "color": "#FF5733",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### 获取标签详情
```http
GET /api/v1/user-tags/{tag_id}
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "880e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "人工智能",
    "color": "#FF5733",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### 创建新标签
```http
POST /api/v1/user-tags
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "人工智能",
  "color": "#FF5733"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "标签创建成功",
  "data": {
    "id": "880e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "人工智能",
    "color": "#FF5733",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### 更新标签
```http
PUT /api/v1/user-tags/{tag_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "AI技术",
  "color": "#33FF57"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "标签更新成功",
  "data": {
    "id": "880e8400-e29b-41d4-a716-446655440000",
    "name": "AI技术",
    "color": "#33FF57",
    "updated_at": "2024-01-15T11:00:00Z"
  }
}
```

### 删除标签
```http
DELETE /api/v1/user-tags/{tag_id}
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "success": true,
  "message": "标签删除成功"
}
```

### 获取标签统计
```http
GET /api/v1/user-tags/stats/overview
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "total_tags": 15,
    "total_insights": 120,
    "most_used_tags": [
      {
        "name": "技术",
        "count": 45,
        "color": "#FF5733"
      },
      {
        "name": "AI",
        "count": 32,
        "color": "#33FF57"
      }
    ],
    "recent_tags": [
      {
        "name": "机器学习",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ]
  }
}
```

### 搜索标签
```http
GET /api/v1/user-tags/search?q=AI&user_id=xxx
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "success": true,
  "data": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440000",
      "name": "人工智能",
      "color": "#FF5733"
    },
    {
      "id": "990e8400-e29b-41d4-a716-446655440000",
      "name": "AI技术",
      "color": "#33FF57"
    }
  ]
}
```

## 👤 用户管理接口

### 上传头像
```http
POST /api/v1/user/upload-avatar
Authorization: Bearer {token}
Content-Type: multipart/form-data

avatar: [File]
user_id: 550e8400-e29b-41d4-a716-446655440000
```

**响应示例：**
```json
{
  "success": true,
  "message": "头像上传成功",
  "data": {
    "avatar_url": "https://example.com/avatars/user123.jpg",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 更新用户资料
```http
PUT /api/v1/user/profile
Authorization: Bearer {token}
Content-Type: application/json

{
  "nickname": "新昵称",
  "bio": "这是我的新个人简介",
  "avatar_url": "https://example.com/new-avatar.jpg"
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "nickname": "新昵称",
    "bio": "这是我的新个人简介",
    "avatar_url": "https://example.com/new-avatar.jpg",
    "updated_at": "2024-01-15T11:00:00Z"
  }
}
```

### 获取用户资料
```http
GET /api/v1/user/profile
Authorization: Bearer {token}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "nickname": "johndoe",
    "avatar_url": "https://example.com/avatar.jpg",
    "bio": "这是我的个人简介",
    "followers_count": 0,
    "following_count": 0,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

## 🏥 系统接口

### 健康检查
```http
GET /api/v1/health
```

**响应示例：**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "database": "connected",
  "uptime": "2h 30m 15s"
}
```

### API信息
```http
GET /api/v1/
```

**响应示例：**
```json
{
  "message": "Welcome to Quest API",
  "version": "1.0.0",
  "docs": "/api/v1/docs",
  "redoc": "/api/v1/redoc",
  "status": "running"
}
```

## ⚠️ 错误响应格式

### 通用错误格式
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "输入数据验证失败",
    "details": [
      {
        "field": "email",
        "message": "邮箱格式不正确"
      }
    ]
  }
}
```

### 常见错误码
- `UNAUTHORIZED`: 未授权访问
- `FORBIDDEN`: 权限不足
- `NOT_FOUND`: 资源不存在
- `VALIDATION_ERROR`: 数据验证失败
- `INTERNAL_ERROR`: 服务器内部错误

## 🔧 请求头要求

### 认证接口
```http
Content-Type: application/json
```

### 需要认证的接口
```http
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 文件上传接口
```http
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

## 📱 使用流程示例

### 1. 用户注册/登录
```javascript
// 注册
const response = await fetch('/api/v1/auth/signup', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123',
    nickname: 'johndoe'
  })
});

// 登录
const loginResponse = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123'
  })
});

const { access_token } = await loginResponse.json();
```

### 2. 提取网页元数据
```javascript
// 提取元数据
const metadataResponse = await fetch('/api/v1/metadata/extract', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'url=https://example.com/article'
});

const metadata = await metadataResponse.json();
```

### 3. 创建insight
```javascript
// 创建insight
const insightResponse = await fetch('/api/v1/insights', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    title: metadata.data.title,
    description: metadata.data.description,
    url: 'https://example.com/article',
    image_url: metadata.data.image_url,
    tags: ['技术', 'AI']
  })
});
```

### 4. 管理标签
```javascript
// 创建标签
const tagResponse = await fetch('/api/v1/user-tags', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
      body: JSON.stringify({
      name: 'AI',
      color: '#FF5733'
    })
});
```

## 🎯 总结

Quest API 提供完整的智能书签和知识管理功能：

- **26个API端点**，覆盖用户、内容、标签等核心功能
- **标准化响应格式**，统一的成功/错误处理
- **完整的CRUD操作**，支持见解、标签管理
- **智能元数据提取**，一键保存网页内容
- **用户认证系统**，支持邮箱密码和Google OAuth
- **用户资料管理**，支持昵称、头像、个人简介

所有接口都遵循RESTful设计原则，支持分页、搜索、筛选等高级功能。

## 📊 数据库结构

1. **`auth.users`** - Supabase认证用户表
2. **`profiles`** - 用户扩展资料表（昵称、头像、简介、关注数）
3. **`insights`** - 用户内容表（标题、描述、URL、图片、标签）
4. **`user_tags`** - 用户标签表（名称、颜色、描述）

没有评论表和关注关系表，所有数据都通过`user_id`关联到`auth.users`。
