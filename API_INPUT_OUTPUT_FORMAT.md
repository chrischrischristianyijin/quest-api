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

## Metadata相关API

### 1. 预览网页元数据
**POST** `/api/v1/metadata/preview`

**功能**: 预览网页的元数据信息，不创建insight

**输入**:
```json
{
  "url": "https://example.com/article"
}
```

**输出**:
```json
{
  "success": true,
  "message": "元数据预览成功",
  "data": {
    "url": "https://example.com/article",
    "title": "文章标题",
    "description": "文章描述",
    "image_url": "https://example.com/image.jpg",
    "domain": "example.com",
    "extracted_at": "2024-01-01T00:00:00.000Z",
    "preview_note": "这是预览，点击创建按钮将保存为insight"
  }
}
```

### 2. 提取网页元数据
**POST** `/api/v1/metadata/extract`

**功能**: 提取网页的元数据信息，不创建insight

**输入**:
```json
{
  "url": "https://example.com/article"
}
```

**输出**:
```json
{
  "success": true,
  "message": "元数据提取成功",
  "data": {
    "url": "https://example.com/article",
    "title": "文章标题",
    "description": "文章描述",
    "image_url": "https://example.com/image.jpg",
    "suggested_tags": [],
    "domain": "example.com",
    "extracted_at": "2024-01-01T00:00:00.000Z"
  }
}
```

### 3. 从URL创建Insight（包含Metadata提取）
**POST** `/api/v1/metadata/create-insight`

**功能**: 先提取网页metadata，再创建insight（两步合一）

**输入**:
```json
{
  "url": "https://example.com/article",
  "title": "自定义标题（可选）",
  "description": "自定义描述（可选）",
  "tags": "tag1,tag2（可选，逗号分隔）"
}
```

**输出**:
```json
{
  "success": true,
  "message": "从URL创建insight成功",
  "data": {
    "id": "uuid",
    "user_id": "user_uuid",
    "url": "https://example.com/article",
    "title": "最终标题",
    "description": "最终描述",
    "image_url": "https://example.com/image.jpg",
    "tags": ["tag1", "tag2"],
    "created_at": "2024-01-01T00:00:00.000Z",
    "updated_at": "2024-01-01T00:00:00.000Z"
  }
}
```

### 4. 批量提取元数据
**POST** `/api/v1/metadata/batch-extract`

**功能**: 批量提取多个URL的元数据

**输入**:
```json
{
  "urls": "https://example1.com\nhttps://example2.com\nhttps://example3.com"
}
```

**输出**:
```json
{
  "success": true,
  "message": "批量元数据提取完成",
  "data": [
    {
      "url": "https://example1.com",
      "success": true,
      "data": {
        "title": "标题1",
        "description": "描述1",
        "image_url": "图片1",
        "domain": "example1.com"
      }
    },
    {
      "url": "https://example2.com",
      "success": true,
      "data": {
        "title": "标题2",
        "description": "描述2",
        "image_url": "图片2",
        "domain": "example2.com"
      }
    }
  ]
}
```

### 5. 预览已保存的Insight
**GET** `/api/v1/metadata/preview/{insight_id}`

**功能**: 预览已保存的insight，并获取URL的最新metadata

**输出**:
```json
{
  "success": true,
  "message": "获取insight预览成功",
  "data": {
    "id": "insight_uuid",
    "user_id": "user_uuid",
    "url": "https://example.com/article",
    "title": "保存的标题",
    "description": "保存的描述",
    "image_url": "保存的图片",
    "tags": ["tag1", "tag2"],
    "created_at": "2024-01-01T00:00:00.000Z",
    "latest_metadata": {
      "title": "最新网页标题",
      "description": "最新网页描述",
      "image_url": "最新网页图片"
    }
  }
}
```

## 工作流程说明

### 方式1：分步操作（推荐）
1. **预览Metadata**: `POST /api/v1/metadata/preview` - 查看网页信息
2. **创建Insight**: `POST /api/v1/insights` - 手动输入内容并保存

### 方式2：一键操作
1. **自动创建**: `POST /api/v1/metadata/create-insight` - 自动提取metadata并创建insight

### 核心字段说明
- **url**: 网页链接（必填）
- **title**: 标题（自动提取或用户自定义）
- **description**: 描述（自动提取或用户自定义）
- **image_url**: 图片地址（自动提取）
- **tags**: 标签数组（用户自定义）

## �� 见解管理接口

### 获取见解列表（分页）
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

### 获取用户所有见解（不分页）
```http
GET /api/v1/insights/all?user_id=xxx&search=AI
Authorization: Bearer {token}
```

**参数说明：**
- `user_id`: 用户ID筛选（可选，不传则默认当前登录用户）
- `search`: 搜索关键词（可选，在标题和描述中搜索）

**功能特点：**
- 一次性获取用户的所有insights，无需分页
- 适合数据量较小的情况（建议<100条）
- 响应格式更简洁，不包含分页信息

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
      },
      {
        "id": "770e8400-e29b-41d4-a716-446655440000",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "url": "https://example.com/article2",
        "title": "机器学习入门指南",
        "description": "从零开始学习机器学习...",
        "image_url": "https://example.com/image2.jpg",
        "tags": ["技术", "机器学习"],
        "created_at": "2024-01-14T10:30:00Z",
        "updated_at": "2024-01-14T10:30:00Z"
      }
    ]
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

### 5. 获取用户所有insights
```javascript
// 获取当前用户的所有insights（不分页）
const insightsResponse = await fetch('/api/v1/insights/all', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

const insightsData = await insightsResponse.json();

if (insightsData.success) {
  const insights = insightsData.data.insights;
  console.log(`用户共有 ${insights.length} 条insights`);
  
  // 渲染所有insights
  insights.forEach(insight => {
    console.log(`- ${insight.title}: ${insight.description}`);
  });
}

// 或者获取指定用户的所有insights
const userInsightsResponse = await fetch('/api/v1/insights/all?user_id=550e8400-e29b-41d4-a716-446655440000', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
```

## 🎯 总结

Quest API 提供完整的智能书签和知识管理功能：

- **27个API端点**，覆盖用户、内容、标签等核心功能
- **标准化响应格式**，统一的成功/错误处理
- **完整的CRUD操作**，支持见解、标签管理
- **智能元数据提取**，一键保存网页内容
- **用户认证系统**，支持邮箱密码和Google OAuth
- **用户资料管理**，支持昵称、头像、个人简介
- **灵活的insights获取**，支持分页和一次性获取所有

所有接口都遵循RESTful设计原则，支持分页、搜索、筛选等高级功能。

## 📊 数据库结构

1. **`auth.users`** - Supabase认证用户表
2. **`profiles`** - 用户扩展资料表（昵称、头像、简介、关注数）
3. **`insights`** - 用户内容表（标题、描述、URL、图片、标签）
4. **`user_tags`** - 用户标签表（名称、颜色、描述）

没有评论表和关注关系表，所有数据都通过`user_id`关联到`auth.users`。
