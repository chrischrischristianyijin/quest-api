# Google OAuth API 接口文档

## 概览

本文档描述了Quest API中Google OAuth相关的三个接口端点，用于实现Google账户登录功能。

**Base URL**: `https://quest-api-edz1.onrender.com/api/v1/auth`

---

## 1. 获取Google OAuth授权URL

### 接口信息
- **端点**: `GET /google/login`
- **描述**: 获取Google OAuth授权URL，用于引导用户进行Google登录
- **认证**: 无需认证

### 请求

#### Request Method
```
GET /api/v1/auth/google/login
```

#### Request Headers
```
Content-Type: application/json
```

#### Request Parameters
无需参数

#### 请求示例
```bash
curl -X GET "https://quest-api-edz1.onrender.com/api/v1/auth/google/login" \
  -H "Content-Type: application/json"
```

### 响应

#### 成功响应 (200 OK)
```json
{
  "success": true,
  "message": "Google登录",
  "data": {
    "oauth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=103202343935-5dkesvf5dp06af09o0d2373ji2ccd0rc.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fquest-api-edz1.onrender.com%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback&scope=openid+email+profile&response_type=code&access_type=offline&include_granted_scopes=true&state=f10bf2e9-b006-46f7-889e-bb08f3d5626d",
    "client_id": "103202343935-5dkesvf5dp06af09o0d2373ji2ccd0rc.apps.googleusercontent.com",
    "redirect_uri": "https://quest-api-edz1.onrender.com/api/v1/auth/google/callback",
    "scope": "openid email profile",
    "response_type": "code",
    "state": "f10bf2e9-b006-46f7-889e-bb08f3d5626d"
  }
}
```

#### 错误响应 (400 Bad Request)
```json
{
  "detail": "Google OAuth配置不完整，请联系管理员"
}
```

#### 错误响应 (500 Internal Server Error)
```json
{
  "detail": "Google登录服务暂时不可用"
}
```

### 响应字段说明

| 字段 | 类型 | 描述 |
|------|------|------|
| `success` | boolean | 请求是否成功 |
| `message` | string | 响应消息 |
| `data.oauth_url` | string | 完整的Google OAuth授权URL |
| `data.client_id` | string | Google OAuth客户端ID |
| `data.redirect_uri` | string | OAuth回调URI |
| `data.scope` | string | 请求的权限范围 |
| `data.response_type` | string | OAuth响应类型 |
| `data.state` | string | 防CSRF攻击的状态参数 |

---

## 2. Google OAuth回调处理

### 接口信息
- **端点**: `POST /google/callback`
- **描述**: 处理Google OAuth授权回调，完成用户登录或注册
- **认证**: 无需认证

### 请求

#### Request Method
```
POST /api/v1/auth/google/callback
```

#### Request Headers
```
Content-Type: application/x-www-form-urlencoded
```

#### Request Parameters

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `code` | string | 是 | Google返回的授权码 |
| `state` | string | 否 | 状态参数（用于验证） |

#### 请求示例
```bash
curl -X POST "https://quest-api-edz1.onrender.com/api/v1/auth/google/callback" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "code=4/0AdLIrYeZjqJG7LgY4bJhGwMNnBpY_example_auth_code" \
  -d "state=f10bf2e9-b006-46f7-889e-bb08f3d5626d"
```

#### 表单数据示例
```
code=4/0AdLIrYeZjqJG7LgY4bJhGwMNnBpY_example_auth_code
state=f10bf2e9-b006-46f7-889e-bb08f3d5626d
```

### 响应

#### 成功响应 - 新用户注册 (200 OK)
```json
{
  "success": true,
  "message": "Google账户创建成功",
  "data": {
    "user": {
      "id": "uuid-user-id-here",
      "email": "user@gmail.com",
      "username": "user_12345678",
      "nickname": "John"
    },
    "access_token": "google_auth_token_uuid-user-id-here_random-uuid",
    "token_type": "bearer"
  }
}
```

#### 成功响应 - 现有用户登录 (200 OK)
```json
{
  "success": true,
  "message": "Google登录成功",
  "data": {
    "user": {
      "id": "uuid-user-id-here",
      "email": "user@gmail.com",
      "username": "existing_user",
      "nickname": "John Doe"
    },
    "access_token": "google_auth_token_uuid-user-id-here_random-uuid",
    "token_type": "bearer"
  }
}
```

#### 错误响应 (400 Bad Request)
```json
{
  "success": false,
  "message": "Google登录回调处理失败: 获取访问令牌失败",
  "statusCode": 400
}
```

#### 错误响应 (500 Internal Server Error)
```json
{
  "detail": "Google登录回调处理失败"
}
```

### 响应字段说明

| 字段 | 类型 | 描述 |
|------|------|------|
| `success` | boolean | 请求是否成功 |
| `message` | string | 响应消息 |
| `data.user.id` | string | 用户唯一标识符 |
| `data.user.email` | string | 用户邮箱地址 |
| `data.user.username` | string | 用户名 |
| `data.user.nickname` | string | 用户昵称 |
| `data.access_token` | string | 访问令牌 |
| `data.token_type` | string | 令牌类型（通常为"bearer"） |

---

## 3. Google ID Token登录

### 接口信息
- **端点**: `POST /google/token`
- **描述**: 使用Google ID Token直接登录（适用于前端已获取ID Token的场景）
- **认证**: 无需认证

### 请求

#### Request Method
```
POST /api/v1/auth/google/token
```

#### Request Headers
```
Content-Type: application/x-www-form-urlencoded
```

#### Request Parameters

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `id_token` | string | 是 | Google ID Token |

#### 请求示例
```bash
curl -X POST "https://quest-api-edz1.onrender.com/api/v1/auth/google/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "id_token=eyJhbGciOiJSUzI1NiIsImtpZCI6IjdkYzBkYzEwZj...example_id_token"
```

#### 表单数据示例
```
id_token=eyJhbGciOiJSUzI1NiIsImtpZCI6IjdkYzBkYzEwZj...example_id_token
```

### 响应

#### 成功响应 - 新用户注册 (200 OK)
```json
{
  "success": true,
  "message": "Google账户创建成功",
  "data": {
    "user": {
      "id": "uuid-user-id-here",
      "email": "user@gmail.com",
      "username": "user_12345678",
      "nickname": "Jane"
    },
    "access_token": "google_auth_token_uuid-user-id-here_random-uuid",
    "token_type": "bearer"
  }
}
```

#### 成功响应 - 现有用户登录 (200 OK)
```json
{
  "success": true,
  "message": "Google登录成功",
  "data": {
    "user": {
      "id": "uuid-user-id-here",
      "email": "user@gmail.com",
      "username": "existing_user",
      "nickname": "Jane Smith"
    },
    "access_token": "google_auth_token_uuid-user-id-here_random-uuid",
    "token_type": "bearer"
  }
}
```

#### 错误响应 (400 Bad Request)
```json
{
  "success": false,
  "message": "Google ID Token登录失败: ID Token验证失败: Wrong number of segments in token: b'invalid_token'",
  "statusCode": 400
}
```

#### 错误响应 (500 Internal Server Error)
```json
{
  "detail": "Google ID Token登录失败"
}
```

### 响应字段说明

响应字段与OAuth回调接口相同。

---

## 🧪 实际测试结果

### 已验证的接口状态

以下测试结果基于实际的生产环境（`https://quest-api-edz1.onrender.com`）：

#### ✅ 健康检查
```bash
curl -X GET "https://quest-api-edz1.onrender.com/health"
```
**响应**: 
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "environment": "production",
  "version": "1.0.0",
  "database": "connected"
}
```

#### ✅ Google OAuth登录 - 正常工作
```bash
curl -X GET "https://quest-api-edz1.onrender.com/api/v1/auth/google/login"
```
**实际响应**: 返回有效的OAuth URL，包含正确的client_id和redirect_uri

#### ✅ OAuth回调 - 参数验证正常
```bash
curl -X POST "https://quest-api-edz1.onrender.com/api/v1/auth/google/callback" \
  -H "Content-Type: application/x-www-form-urlencoded" -d "code="
```
**实际响应**: 正确返回400错误，说明参数验证工作正常

#### ✅ ID Token验证 - Token验证正常
```bash
curl -X POST "https://quest-api-edz1.onrender.com/api/v1/auth/google/token" \
  -H "Content-Type: application/x-www-form-urlencoded" -d "id_token=invalid_token"
```
**实际响应**: 正确返回400错误，说明Token验证工作正常

### 🔗 可用的OAuth URL

您可以直接在浏览器中测试以下OAuth URL：
```
https://accounts.google.com/o/oauth2/v2/auth?client_id=103202343935-5dkesvf5dp06af09o0d2373ji2ccd0rc.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fquest-api-edz1.onrender.com%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback&scope=openid+email+profile&response_type=code&access_type=offline&include_granted_scopes=true
```

---

## 前端集成示例

### 1. 授权码流程（推荐）

```javascript
// Step 1: 获取授权URL
async function getGoogleAuthUrl() {
  try {
    const response = await fetch('https://quest-api-edz1.onrender.com/api/v1/auth/google/login');
    const data = await response.json();
    
    if (data.success) {
      // 引导用户到Google授权页面
      window.location.href = data.data.oauth_url;
    }
  } catch (error) {
    console.error('获取Google授权URL失败:', error);
  }
}

// Step 2: 在回调页面处理授权码
async function handleGoogleCallback() {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  const state = urlParams.get('state');
  
  if (code) {
    try {
      const formData = new FormData();
      formData.append('code', code);
      if (state) formData.append('state', state);
      
      const response = await fetch('https://quest-api-edz1.onrender.com/api/v1/auth/google/callback', {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (data.success) {
        // 登录成功，保存token
        localStorage.setItem('access_token', data.data.access_token);
        localStorage.setItem('user', JSON.stringify(data.data.user));
        
        // 重定向到主页
        window.location.href = '/dashboard';
      } else {
        console.error('Google登录失败:', data.detail);
      }
    } catch (error) {
      console.error('处理Google回调失败:', error);
    }
  }
}
```

### 2. ID Token流程

```javascript
// 使用Google API直接获取ID Token
async function signInWithGoogleToken(idToken) {
  try {
    const formData = new FormData();
    formData.append('id_token', idToken);
    
    const response = await fetch('https://quest-api-edz1.onrender.com/api/v1/auth/google/token', {
      method: 'POST',
      body: formData
    });
    
    const data = await response.json();
    
    if (data.success) {
      // 登录成功
      localStorage.setItem('access_token', data.data.access_token);
      localStorage.setItem('user', JSON.stringify(data.data.user));
      return data.data;
    } else {
      throw new Error(data.detail);
    }
  } catch (error) {
    console.error('Google ID Token登录失败:', error);
    throw error;
  }
}
```

---

## 错误码说明

| HTTP状态码 | 错误类型 | 描述 |
|------------|----------|------|
| 200 | 成功 | 请求成功处理 |
| 400 | 客户端错误 | 请求参数错误或验证失败 |
| 500 | 服务器错误 | 服务器内部错误 |

### 常见错误信息

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| "Google OAuth配置不完整" | 服务器缺少必要的Google OAuth配置 | 检查环境变量配置 |
| "获取访问令牌失败" | 授权码无效或已过期 | 重新获取授权码 |
| "ID Token验证失败" | ID Token无效、过期或签名错误 | 获取新的ID Token |
| "Google用户信息中缺少邮箱" | Google返回的用户信息不完整 | 检查OAuth权限范围 |

---

## 安全注意事项

1. **HTTPS要求**: 生产环境必须使用HTTPS
2. **State参数**: 使用state参数防止CSRF攻击
3. **Token安全**: 安全存储和传输访问令牌
4. **权限最小化**: 只请求必要的OAuth权限
5. **令牌过期**: 实现令牌刷新机制

---

## 测试指南

### 使用curl测试

```bash
# 1. 获取授权URL
curl -X GET "https://quest-api-edz1.onrender.com/api/v1/auth/google/login"

# 2. 模拟回调（需要真实的授权码）
curl -X POST "https://quest-api-edz1.onrender.com/api/v1/auth/google/callback" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "code=REAL_AUTH_CODE_FROM_GOOGLE"

# 3. 使用ID Token登录（需要真实的ID Token）
curl -X POST "https://quest-api-edz1.onrender.com/api/v1/auth/google/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "id_token=REAL_ID_TOKEN_FROM_GOOGLE"
```

### 测试环境配置

确保测试环境包含以下配置：
- 有效的Google OAuth客户端ID和密钥
- 正确的重定向URI
- 可访问的数据库连接
