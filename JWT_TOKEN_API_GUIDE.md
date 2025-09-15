# JWT Token 管理 API 指南

## 📋 概述

本文档记录了新增的 JWT Token 管理相关 API 端点，用于解决 "Login validation failed" 问题和提供完整的 token 生命周期管理。

## 🔧 新增 API 端点

### 1. Token 刷新 API

#### 刷新访问令牌
```http
POST /api/v1/auth/refresh
Content-Type: application/x-www-form-urlencoded
```

**请求参数：**
- `refresh_token` (string, required): 刷新令牌

**请求示例：**
```bash
curl -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "refresh_token=your_refresh_token_here" \
  http://localhost:8080/api/v1/auth/refresh
```

**成功响应 (200)：**
```json
{
  "success": true,
  "message": "令牌刷新成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "new_refresh_token_here",
    "token_type": "bearer",
    "expires_at": 1703123456,
    "expires_in": 86400
  }
}
```

**错误响应 (401)：**
```json
{
  "detail": "令牌刷新失败，请重新登录"
}
```

---

### 2. Token 状态检查 API

#### 检查 Token 状态和剩余时间
```http
GET /api/v1/auth/token-status
Authorization: Bearer {access_token}
```

**请求示例：**
```bash
curl -H "Authorization: Bearer your_access_token_here" \
     http://localhost:8080/api/v1/auth/token-status
```

**成功响应 (200)：**
```json
{
  "success": true,
  "data": {
    "token_length": 200,
    "token_prefix": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "is_google_token": false,
    "is_jwt_format": true,
    "expires_at": 1703123456,
    "expires_at_readable": "2023-12-21 15:30:56",
    "time_remaining": 1800,
    "is_expired": false,
    "hours_remaining": 0,
    "minutes_remaining": 30,
    "validation_status": "success",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_email": "user@example.com"
  }
}
```

**字段说明：**
- `token_length`: Token 长度
- `token_prefix`: Token 前缀（前20字符）
- `is_google_token`: 是否为 Google 登录 token
- `is_jwt_format`: 是否为标准 JWT 格式
- `expires_at`: 过期时间戳
- `expires_at_readable`: 可读的过期时间
- `time_remaining`: 剩余秒数
- `is_expired`: 是否已过期
- `hours_remaining`: 剩余小时数
- `minutes_remaining`: 剩余分钟数
- `validation_status`: 验证状态 ("success" | "failed")
- `user_id`: 用户ID
- `user_email`: 用户邮箱

---

### 3. Token 调试 API

#### 调试 Token 验证
```http
POST /api/v1/auth/debug-token
Authorization: Bearer {access_token}
```

**请求示例：**
```bash
curl -X POST \
  -H "Authorization: Bearer your_access_token_here" \
  http://localhost:8080/api/v1/auth/debug-token
```

**成功响应 (200)：**
```json
{
  "success": true,
  "data": {
    "raw_header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "header_length": 200,
    "has_authorization_header": true,
    "token_length": 194,
    "token_prefix": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "is_google_token": false,
    "is_jwt_format": true,
    "validation_status": "success",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_email": "user@example.com"
  }
}
```

---

## 🔄 增强的现有 API

### 登录 API 增强

#### 用户登录（增强版）
```http
POST /api/v1/auth/login
Content-Type: application/json
```

**请求体：**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**增强的响应：**
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "refresh_token_here",
    "token_type": "bearer",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "expires_at": 1703123456,
    "expires_in": 86400,
    "session": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**新增字段：**
- `refresh_token`: 刷新令牌
- `expires_at`: 过期时间戳
- `expires_in`: 有效期（秒）

---

## 🛠️ 前端集成示例

### JavaScript 实现

#### 1. Token 管理类
```javascript
class TokenManager {
  constructor() {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
    this.expiresAt = localStorage.getItem('expires_at');
  }

  // 检查 token 是否即将过期（1小时内）
  isTokenExpiringSoon() {
    if (!this.expiresAt) return false;
    const timeRemaining = this.expiresAt - Date.now() / 1000;
    return timeRemaining < 3600; // 1小时内过期
  }

  // 检查 token 是否已过期
  isTokenExpired() {
    if (!this.expiresAt) return true;
    return this.expiresAt <= Date.now() / 1000;
  }

  // 自动刷新 token
  async refreshTokenIfNeeded() {
    if (this.isTokenExpiringSoon()) {
      try {
        const response = await fetch('/api/v1/auth/refresh', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: `refresh_token=${this.refreshToken}`
        });

        if (response.ok) {
          const data = await response.json();
          this.updateTokens(data.data);
          return true;
        }
      } catch (error) {
        console.error('Token refresh failed:', error);
      }
    }
    return false;
  }

  // 更新 token 信息
  updateTokens(tokenData) {
    this.accessToken = tokenData.access_token;
    this.refreshToken = tokenData.refresh_token;
    this.expiresAt = tokenData.expires_at;
    
    localStorage.setItem('access_token', this.accessToken);
    localStorage.setItem('refresh_token', this.refreshToken);
    localStorage.setItem('expires_at', this.expiresAt);
  }

  // 获取有效的 Authorization header
  async getAuthHeader() {
    await this.refreshTokenIfNeeded();
    return `Bearer ${this.accessToken}`;
  }
}
```

#### 2. API 请求拦截器
```javascript
// 使用 axios 的请求拦截器
axios.interceptors.request.use(async (config) => {
  const tokenManager = new TokenManager();
  
  // 自动添加 Authorization header
  if (config.url.includes('/api/v1/')) {
    config.headers.Authorization = await tokenManager.getAuthHeader();
  }
  
  return config;
});

// 响应拦截器处理 token 过期
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const tokenManager = new TokenManager();
      
      // 尝试刷新 token
      const refreshed = await tokenManager.refreshTokenIfNeeded();
      
      if (refreshed) {
        // 重试原请求
        error.config.headers.Authorization = await tokenManager.getAuthHeader();
        return axios.request(error.config);
      } else {
        // 跳转到登录页面
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);
```

#### 3. Token 状态监控
```javascript
// 定期检查 token 状态
async function checkTokenStatus() {
  try {
    const response = await fetch('/api/v1/auth/token-status', {
      headers: {
        'Authorization': await tokenManager.getAuthHeader()
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      const tokenInfo = data.data;
      
      console.log('Token Status:', {
        expiresAt: tokenInfo.expires_at_readable,
        timeRemaining: `${tokenInfo.hours_remaining}h ${tokenInfo.minutes_remaining}m`,
        isExpired: tokenInfo.is_expired
      });
      
      // 如果即将过期，显示提醒
      if (tokenInfo.hours_remaining < 1) {
        showNotification('Token 即将过期，正在自动刷新...');
      }
    }
  } catch (error) {
    console.error('Token status check failed:', error);
  }
}

// 每30分钟检查一次
setInterval(checkTokenStatus, 30 * 60 * 1000);
```

---

## 🔍 故障排除

### 常见问题

#### 1. "Token已过期，请使用refresh token或重新登录"
**原因：** JWT token 已超过 24 小时有效期
**解决方案：**
- 使用 refresh token 刷新
- 重新登录获取新 token

#### 2. "Token格式无效：不是有效的JWT格式"
**原因：** Token 不是标准的 JWT 格式
**解决方案：**
- 检查 token 是否包含两个点分隔的三部分
- 确认使用的是 Supabase 生成的 JWT token

#### 3. "Token刷新失败，请重新登录"
**原因：** Refresh token 无效或已过期
**解决方案：**
- 清除本地存储的 token
- 重新登录获取新的 token 对

### 调试步骤

1. **检查 token 状态：**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:8080/api/v1/auth/token-status
   ```

2. **查看后端日志：**
   - 启动服务后查看详细的 token 验证日志
   - 包括过期时间、剩余时间等信息

3. **测试刷新功能：**
   ```bash
   curl -X POST -d "refresh_token=YOUR_REFRESH_TOKEN" \
        http://localhost:8080/api/v1/auth/refresh
   ```

---

## 📊 配置说明

### Supabase JWT 配置
- **Access Token 过期时间**: 86400 秒（24小时）
- **JWT Secret**: 用于签名和验证 JWT
- **建议**: 使用 JWT Signing Keys 替代 Legacy JWT Secret

### 环境变量
确保以下环境变量正确配置：
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

---

## 🚀 最佳实践

1. **前端 Token 管理：**
   - 定期检查 token 状态
   - 在过期前自动刷新
   - 处理刷新失败的情况

2. **安全性：**
   - 不要在 URL 中传递 token
   - 使用 HTTPS 传输
   - 定期轮换 refresh token

3. **用户体验：**
   - 无感知的 token 刷新
   - 清晰的错误提示
   - 自动重试机制

4. **监控：**
   - 记录 token 使用情况
   - 监控刷新频率
   - 跟踪验证失败原因

---

## 📝 更新日志

- **v1.0.0** (2024-01-15): 初始版本
  - 添加 token 刷新 API
  - 添加 token 状态检查 API
  - 添加 token 调试 API
  - 增强登录 API 响应
  - 改进 JWT 验证逻辑
  - 添加过期时间检查
  - 统一 Google token 管理
