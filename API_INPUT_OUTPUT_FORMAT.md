# Quest API 完整接口文档

## 📋 API端点总览

### **认证接口 (4个)**
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/signup` - 用户注册（别名）
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/signout` - 用户登出

### **用户管理接口 (2个)**
- `GET /api/v1/user/profile` - 获取用户资料
- `PUT /api/v1/user/profile` - 更新用户资料

### **见解管理接口 (6个)**
- `GET /api/v1/insights` - 获取用户见解列表（分页）
- `GET /api/v1/insights/all` - 获取用户所有见解
- `GET /api/v1/insights/{insight_id}` - 获取单个见解详情
- `POST /api/v1/insights` - 创建新见解
- `PUT /api/v1/insights/{insight_id}` - 更新见解
- `DELETE /api/v1/insights/{insight_id}` - 删除见解

### **用户标签管理接口 (5个)**
- `GET /api/v1/user-tags` - 获取用户标签列表
- `GET /api/v1/user-tags/{tag_id}` - 获取单个标签详情
- `POST /api/v1/user-tags` - 创建新标签
- `PUT /api/v1/user-tags/{tag_id}` - 更新标签
- `DELETE /api/v1/user-tags/{tag_id}` - 删除标签

### **元数据提取接口 (2个)**
- `POST /api/v1/metadata/extract` - 提取网页元数据
- `POST /api/v1/metadata/create-insight` - 从URL创建见解

### **系统接口 (2个)**
- `GET /` - API根路径
- `GET /health` - 健康检查

**总计：21个API端点**

---

## 🔐 认证系统接口

### 用户注册
```http
POST /api/v1/auth/register
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

## 🧠 见解管理接口

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
        "title": "AI技术发展趋势",
        "description": "关于人工智能的最新发展...",
        "url": "https://example.com/article",
        "image_url": "https://example.com/image.jpg",
        "thought": "这个领域发展很快，值得深入研究",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
        "tags": [
          {
            "id": "880e8400-e29b-41d4-a716-446655440000",
            "name": "技术",
            "color": "#3B82F6"
          },
          {
            "id": "990e8400-e29b-41d4-a716-446655440000",
            "name": "AI",
            "color": "#10B981"
          }
        ]
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
        "title": "AI技术发展趋势",
        "description": "关于人工智能的最新发展...",
        "url": "https://example.com/article",
        "image_url": "https://example.com/image.jpg",
        "thought": "这个领域发展很快，值得深入研究",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
        "tags": [
          {
            "id": "880e8400-e29b-41d4-a716-446655440000",
            "name": "技术",
            "color": "#3B82F6"
          },
          {
            "id": "990e8400-e29b-41d4-a716-446655440000",
            "name": "AI",
            "color": "#10B981"
          }
        ]
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
- 如果尝试访问其他用户的insight，返回400错误

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "AI技术发展趋势",
    "description": "关于人工智能的最新发展...",
    "url": "https://example.com/article",
    "image_url": "https://example.com/image.jpg",
    "thought": "这个领域发展很快，值得深入研究",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "tags": [
      {
        "id": "880e8400-e29b-41d4-a716-446655440000",
        "name": "技术",
        "color": "#3B82F6"
      },
      {
        "id": "990e8400-e29b-41d4-a716-446655440000",
        "name": "AI",
        "color": "#10B981"
      }
    ]
  }
}
```

### 创建新见解
```http
POST /api/v1/insights
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "AI技术发展趋势",
  "description": "关于人工智能的最新发展...",
  "url": "https://example.com/article",
  "image_url": "https://example.com/image.jpg",
  "thought": "这个领域发展很快，值得深入研究",
  "tag_names": ["技术", "AI", "机器学习"]
}
```

**字段说明：**
- **`title`** (必需): 见解标题，1-200字符
- **`description`** (可选): 见解描述，最大3000字符
- **`url`** (可选): 相关链接，最大500字符
- **`image_url`** (可选): 图片地址，最大500字符
- **`thought`** (可选): 用户的想法/备注，最大2000字符
- **`tag_names`** (可选): 标签名称数组，会自动创建或关联现有标签

**标签处理逻辑：**
- 前端传入标签名称数组：`["技术", "AI", "机器学习"]`
- 后端智能处理：
  1. 检查用户是否已有同名标签
  2. 如果存在，使用现有标签的ID
  3. 如果不存在，自动创建新标签并分配颜色
  4. 通过 `insight_tags` 表建立多对多关联关系
- 响应中返回完整的标签对象（包含ID、名称、颜色等）

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "AI技术发展趋势",
    "description": "关于人工智能的最新发展...",
    "url": "https://example.com/article",
    "image_url": "https://example.com/image.jpg",
    "thought": "这个领域发展很快，值得深入研究",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:00:00Z",
    "tags": [
      {
        "id": "880e8400-e29b-41d4-a716-446655440000",
        "name": "技术",
        "color": "#3B82F6"
      },
      {
        "id": "990e8400-e29b-41d4-a716-446655440000",
        "name": "AI",
        "color": "#10B981"
      },
      {
        "id": "aa0e8400-e29b-41d4-a716-446655440000",
        "name": "机器学习",
        "color": "#8B5CF6"
      }
    ]
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
  "thought": "更新后的想法和备注",
  "tag_names": ["技术", "AI", "机器学习"]
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "更新后的标题",
    "description": "更新后的描述",
    "url": "https://example.com/article",
    "image_url": "https://example.com/image.jpg",
    "thought": "更新后的想法和备注",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:00:00Z",
    "tags": [
      {
        "id": "880e8400-e29b-41d4-a716-446655440000",
        "name": "技术",
        "color": "#3B82F6"
      },
      {
        "id": "990e8400-e29b-41d4-a716-446655440000",
        "name": "AI",
        "color": "#10B981"
      },
      {
        "id": "aa0e8400-e29b-41d4-a716-446655440000",
        "name": "机器学习",
        "color": "#8B5CF6"
      }
    ]
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
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
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
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
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

**字段说明：**
- **`name`** (必需): 标签名称，1-50字符
- **`color`** (必需): 标签颜色，十六进制格式（如 #FF5733）

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
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
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
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "AI技术",
    "color": "#33FF57",
    "created_at": "2024-01-15T10:30:00Z",
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

## 🔗 标签管理说明

### 新的标签管理方式

**重要变化：**
- 原来：insights表直接存储 `tags` 数组字段
- 现在：通过 `tag_names` 字段管理标签，后端自动处理关联关系

### 多用户标签名称处理

**当前设计特点：**
- **标签名称可以重复**：不同用户可以使用相同的标签名称（如 "AI"、"技术"、"学习"）
- **标签ID唯一**：每个标签都有全局唯一的UUID，避免冲突
- **用户隔离**：标签通过user_id关联到特定用户，确保数据安全
- **智能匹配**：创建insight时，优先使用用户自己的标签，不存在则自动创建

### 标签命名冲突处理

#### 场景示例
```
用户A: 标签 "AI" (ID: uuid-1, 颜色: #3B82F6)
用户B: 标签 "AI" (ID: uuid-2, 颜色: #10B981)  
用户C: 标签 "AI" (ID: uuid-3, 颜色: #8B5CF6)
```

#### 处理逻辑
1. **创建insight时**：
   - 用户A使用标签 "AI" → 使用uuid-1
   - 用户B使用标签 "AI" → 使用uuid-2
   - 用户C使用标签 "AI" → 使用uuid-3

2. **标签管理**：
   - 每个用户只能看到和管理自己的标签
   - 标签名称可以重复，但ID和颜色可能不同
   - 支持个性化标签颜色设置

### 使用方式

#### 创建/更新insight时管理标签
```javascript
// 创建insight时指定标签
const response = await fetch('/api/v1/insights', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    title: "AI技术发展趋势",
    description: "关于人工智能的最新发展...",
    url: "https://example.com/article",
    tag_names: ["AI", "技术", "趋势"]  // 智能匹配：优先使用现有标签，不存在则创建
  })
});

// 更新insight时修改标签
const updateResponse = await fetch(`/api/v1/insights/${insightId}`, {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    title: "更新后的标题",
    tag_names: ["AI", "机器学习", "深度学习"]  // 完全替换现有标签
  })
});
```

### 2. 创建insight
```javascript
// 直接创建insight
const insightResponse = await fetch('/api/v1/insights', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    title: "AI技术发展趋势",
    description: "关于人工智能的最新发展...",
    url: "https://example.com/article",
    image_url: "https://example.com/image.jpg",
    thought: "这个领域发展很快，值得深入研究，我计划深入学习机器学习和深度学习",
    tag_names: ['技术', 'AI', '机器学习']  // 使用标签名称，后端自动处理
  })
});

const insightData = await insightResponse.json();
if (insightData.success) {
  console.log('Insight创建成功:', insightData.data);
  console.log('标签信息:', insightData.data.tags);
}
```

### 3. 从URL创建insight
```javascript
// 从URL创建insight（自动提取metadata）
const insightResponse = await fetch('/api/v1/metadata/create-insight', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Authorization': `Bearer ${access_token}`
  },
  body: new URLSearchParams({
    url: 'https://example.com/article',
    title: '自定义标题（可选）',
    description: '自定义描述（可选）',
    thought: '这个领域发展很快，值得深入研究，我计划深入学习机器学习和深度学习',
    tags: '技术,AI,机器学习'  // 逗号分隔的标签
  })
});

const insightData = await insightResponse.json();
if (insightData.success) {
  console.log('Insight创建成功:', insightData.data);
  console.log('标签信息:', insightData.data.tags);
}
```

### 标签自动处理

**后端智能完成：**
1. **标签查找**：优先查找用户是否已有同名标签
2. **标签创建**：如果不存在，自动创建新标签并分配随机颜色
3. **关联管理**：自动管理insight和标签的多对多关联关系
4. **权限控制**：确保用户只能访问自己的标签

**前端无需关心：**
- 标签是否已存在的检查
- 标签的创建和更新逻辑
- 标签关联关系的底层实现
- 数据完整性检查

### 标签颜色管理

**自动颜色分配：**
- 新创建的标签自动分配预定义的美观颜色
- 颜色从预定义调色板中随机选择
- 支持16种不同的颜色选项
- 确保视觉区分度和美观性

**颜色示例：**
```css
#3B82F6 (蓝色)  #10B981 (绿色)  #8B5CF6 (紫色)
#EF4444 (红色)  #F59E0B (橙色)  #06B6D4 (青色)
#84CC16 (青绿)  #F97316 (橙红)  #EC4899 (粉色)
#6366F1 (靛蓝)  #14B8A6 (青蓝)  #F43F5E (玫红)
```

## 📊 Metadata相关API

### 1. 提取网页元数据
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

### 2. 从URL创建Insight（包含Metadata提取）
**POST** `/api/v1/metadata/create-insight`

**功能**: 先提取网页metadata，再创建insight（两步合一）

**输入**:
```json
{
  "url": "https://example.com/article",
  "title": "自定义标题（可选）",
  "description": "自定义描述（可选）",
  "image_url": "自定义图片（可选）",
  "thought": "用户的想法/备注（可选）",
  "tags": "tag1,tag2"（可选，标签名称，逗号分隔）
}
```

**字段说明：**
- **`url`** (必需): 网页链接
- **`title`** (可选): 自定义标题，如果不提供则使用网页自动提取的标题
- **`description`** (可选): 自定义描述，如果不提供则使用网页自动提取的描述，最大3000字符
- **`image_url`** (可选): 自定义图片地址，如果不提供则使用网页自动提取的图片
- **`thought`** (可选): 用户的想法/备注，最大2000字符
- **`tags`** (可选): 标签名称，逗号分隔的字符串，如 "AI,技术,趋势"

**标签处理逻辑：**
- 前端传入标签字符串：`"AI,技术,趋势"`
- 后端自动分割并处理标签名称
- 智能匹配现有标签或创建新标签
- 通过 `insight_tags` 表建立关联关系

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
    "thought": "用户的想法/备注",
    "created_at": "2024-01-01T00:00:00.000Z",
    "updated_at": "2024-01-01T00:00:00.000Z",
    "tags": [
      {
        "id": "tag-uuid-1",
        "name": "AI",
        "color": "#3B82F6"
      },
      {
        "id": "tag-uuid-2", 
        "name": "技术",
        "color": "#10B981"
      },
      {
        "id": "tag-uuid-3",
        "name": "趋势",
        "color": "#8B5CF6"
      }
    ]
  }
}
```

## 👤 用户管理接口

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
    "created_at": "2024-01-15T10:30:00Z",
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
    "email": "user@example.com",
    "nickname": "新昵称",
    "bio": "这是我的新个人简介",
    "avatar_url": "https://example.com/new-avatar.jpg",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T11:00:00Z"
  }
}
```

## 🏥 系统接口

### 健康检查
```http
GET /health
```

**响应示例：**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "environment": "development",
  "version": "1.0.0",
  "database": "connected"
}
```

### API信息
```http
GET /
```

**响应示例：**
```json
{
  "message": "Welcome to Quest API",
  "version": "1.0.0",
  "docs": "/api/v1/docs"
}
```

## ⚠️ 错误响应格式

### 通用错误格式
```json
{
  "success": false,
  "detail": "具体错误信息"
}
```

### 常见错误码
- `401 UNAUTHORIZED`: 未授权访问
- `403 FORBIDDEN`: 权限不足
- `404 NOT_FOUND`: 资源不存在
- `422 UNPROCESSABLE_ENTITY`: 数据验证失败
- `500 INTERNAL_SERVER_ERROR`: 服务器内部错误

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
const response = await fetch('/api/v1/auth/register', {
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

const { data: { access_token } } = await loginResponse.json();
```

### 2. 创建insight
```javascript
// 直接创建insight
const insightResponse = await fetch('/api/v1/insights', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    title: "AI技术发展趋势",
    description: "关于人工智能的最新发展...",
    url: "https://example.com/article",
    image_url: "https://example.com/image.jpg",
    thought: "这个领域发展很快，值得深入研究，我计划深入学习机器学习和深度学习",
    tag_names: ['技术', 'AI', '机器学习']  // 使用标签名称，后端自动处理
  })
});

const insightData = await insightResponse.json();
if (insightData.success) {
  console.log('Insight创建成功:', insightData.data);
  console.log('标签信息:', insightData.data.tags);
}
```

### 3. 从URL创建insight
```javascript
// 从URL创建insight（自动提取metadata）
const insightResponse = await fetch('/api/v1/metadata/create-insight', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Authorization': `Bearer ${access_token}`
  },
  body: new URLSearchParams({
    url: 'https://example.com/article',
    title: '自定义标题（可选）',
    description: '自定义描述（可选）',
    thought: '这个领域发展很快，值得深入研究，我计划深入学习机器学习和深度学习',
    tags: '技术,AI,机器学习'  // 逗号分隔的标签
  })
});

const insightData = await insightResponse.json();
if (insightData.success) {
  console.log('Insight创建成功:', insightData.data);
  console.log('标签信息:', insightData.data.tags);
}
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

const tagData = await tagResponse.json();
if (tagData.success) {
  console.log('标签创建成功:', tagData.data);
}
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
    console.log(`  标签: ${insight.tags.map(tag => tag.name).join(', ')}`);
  });
}
```

## 🎯 总结

Quest API 提供完整的智能书签和知识管理功能：

- **21个API端点**，覆盖用户、内容、标签等核心功能
- **标准化响应格式**，统一的成功/错误处理
- **完整的CRUD操作**，支持见解、标签管理
- **智能元数据提取**，一键保存网页内容
- **用户认证系统**，支持邮箱密码和Google OAuth
- **用户资料管理**，支持昵称、头像、个人简介
- **灵活的insights获取**，支持分页和一次性获取所有
- **多对多标签关联**，通过桥表管理insights和tags的关系
- **灵活的insight创建**：支持直接创建和从URL创建两种方式

## 📊 数据库结构

1. **`auth.users`** - Supabase认证用户表（系统表）
   - id (UUID) - 主键，被所有其他表外键引用
   - email, encrypted_password, last_sign_in 等（Supabase自动管理）

2. **`profiles`** - 用户资料表
   - id (UUID) - 外键 → auth.users.id，一对一关系
   - nickname (TEXT) - 用户昵称
   - avatar_url (TEXT) - 用户头像链接
   - bio (TEXT) - 个人简介
   - created_at, updated_at (TIMESTAMP) - 时间戳

3. **`insights`** - 用户内容表
   - id (UUID) - 主键，数据库自动生成
   - user_id (UUID) - 外键 → auth.users.id
   - url (TEXT) - 相关网址
   - title (TEXT) - 见解标题
   - description (TEXT) - 描述信息
   - image_url (TEXT) - 配图链接
   - thought (TEXT) - 用户的想法/备注（自由文本）
   - created_at, updated_at (TIMESTAMP) - 时间戳

4. **`user_tags`** - 用户自定义标签表
   - id (UUID) - 主键，数据库自动生成
   - user_id (UUID) - 外键 → auth.users.id
   - name (TEXT) - 标签名字
   - color (TEXT) - 标签颜色（UI区分用）
   - created_at, updated_at (TIMESTAMP) - 时间戳

5. **`insight_tags`** - 多对多关系表
   - id (UUID) - 主键，数据库自动生成
   - insight_id (UUID) - 外键 → insights.id
   - tag_id (UUID) - 外键 → user_tags.id
   - user_id (UUID) - 外键 → auth.users.id（冗余存储，便于权限控制）
   - created_at (TIMESTAMP) - 时间戳

**数据关联关系：**
- auth.users ↔ profiles (一对一)
- auth.users ↔ insights (一对多)
- auth.users ↔ user_tags (一对多)
- insights ↔ insight_tags ↔ user_tags (多对多)

**权限控制：**
- 所有业务表都通过user_id关联到auth.users
- 用户只能访问和操作自己的数据
- 支持级联删除（删除insight时自动删除相关标签关联）

**UUID生成策略：**
- 所有表的主键UUID字段由数据库自动生成（DEFAULT gen_random_uuid()）
- 避免应用层手动生成UUID，防止冲突

**Insight创建策略：**
- 支持两种创建方式：
  1. 直接创建：用户手动输入所有内容
  2. 从URL创建：自动提取网页metadata，支持用户自定义覆盖
- 智能标签管理和关联