# 🚀 Quest API 前端集成指南

## 📋 概述

Quest API 是一个基于 FastAPI 的后端服务，提供完整的用户认证、见解管理、标签系统等功能。本文档将指导您如何在前端项目中集成这些 API。

## 🔗 API 基础信息

- **基础URL**: `http://localhost:3001` (本地开发)
- **API版本**: `/api/v1`
- **完整API地址**: `http://localhost:3001/api/v1`
- **文档地址**: `http://localhost:3001/api/v1/docs`
- **健康检查**: `http://localhost:3001/api/v1/health`

## 🛠️ 前端集成方式

### 1. **原生 JavaScript/Fetch API**

```javascript
// API配置
const API_BASE = 'http://localhost:3001/api/v1';

// 健康检查
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        console.log('API状态:', data);
    } catch (error) {
        console.error('API连接失败:', error);
    }
}

// 用户登录
async function login(email, password) {
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('authToken', data.token);
            return data;
        } else {
            throw new Error('登录失败');
        }
    } catch (error) {
        console.error('登录错误:', error);
        throw error;
    }
}
```

### 2. **React 集成**

```jsx
import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:3001/api/v1';

function QuestAPI() {
    const [insights, setInsights] = useState([]);
    const [loading, setLoading] = useState(false);

    // 获取见解列表
    const fetchInsights = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE}/insights`);
            const data = await response.json();
            setInsights(data.insights || []);
        } catch (error) {
            console.error('获取见解失败:', error);
        } finally {
            setLoading(false);
        }
    };

    // 创建见解
    const createInsight = async (insightData) => {
        const token = localStorage.getItem('authToken');
        try {
            const response = await fetch(`${API_BASE}/insights`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(insightData)
            });

            if (response.ok) {
                await fetchInsights(); // 刷新列表
                return true;
            }
        } catch (error) {
            console.error('创建见解失败:', error);
        }
        return false;
    };

    useEffect(() => {
        fetchInsights();
    }, []);

    return (
        <div>
            <h2>见解列表</h2>
            {loading ? (
                <p>加载中...</p>
            ) : (
                <div>
                    {insights.map(insight => (
                        <div key={insight.id}>
                            <h3>{insight.title}</h3>
                            <p>{insight.description}</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default QuestAPI;
```

### 3. **Vue.js 集成**

```vue
<template>
  <div>
    <h2>用户资料</h2>
    <div v-if="user">
      <p>用户名: {{ user.username }}</p>
      <p>邮箱: {{ user.email }}</p>
    </div>
    <button @click="fetchProfile">获取资料</button>
  </div>
</template>

<script>
const API_BASE = 'http://localhost:3001/api/v1';

export default {
  data() {
    return {
      user: null
    };
  },
  methods: {
    async fetchProfile() {
      const token = localStorage.getItem('authToken');
      if (!token) {
        alert('请先登录');
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/user/profile`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          this.user = data.user;
        }
      } catch (error) {
        console.error('获取用户资料失败:', error);
      }
    }
  }
};
</script>
```

### 4. **Angular 集成**

```typescript
// quest.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

const API_BASE = 'http://localhost:3001/api/v1';

@Injectable({
  providedIn: 'root'
})
export class QuestService {
  constructor(private http: HttpClient) {}

  // 获取见解列表
  getInsights(): Observable<any> {
    return this.http.get(`${API_BASE}/insights`);
  }

  // 创建见解
  createInsight(insightData: any): Observable<any> {
    const token = localStorage.getItem('authToken');
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });

    return this.http.post(`${API_BASE}/insights`, insightData, { headers });
  }

  // 用户登录
  login(credentials: { email: string; password: string }): Observable<any> {
    return this.http.post(`${API_BASE}/auth/login`, credentials);
  }
}
```

## 🔐 认证流程

### 1. **用户注册**
```javascript
const signupData = {
    email: 'user@example.com',
    password: 'password123',
    username: 'username'
};

const response = await fetch(`${API_BASE}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(signupData)
});
```

### 2. **用户登录**
```javascript
const loginData = {
    email: 'user@example.com',
    password: 'password123'
};

const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(loginData)
});

const data = await response.json();
localStorage.setItem('authToken', data.token);
```

### 3. **使用认证Token**
```javascript
const token = localStorage.getItem('authToken');

// 在请求头中添加认证
const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
};

const response = await fetch(`${API_BASE}/user/profile`, {
    headers: headers
});
```

## 📱 移动端集成

### React Native
```javascript
import { Alert } from 'react-native';

const API_BASE = 'http://localhost:3001/api/v1';

const fetchInsights = async () => {
    try {
        const response = await fetch(`${API_BASE}/insights`);
        const data = await response.json();
        return data.insights;
    } catch (error) {
        Alert.alert('错误', '获取数据失败');
        return [];
    }
};
```

### Flutter
```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class QuestAPI {
  static const String baseUrl = 'http://localhost:3001/api/v1';

  static Future<List<dynamic>> getInsights() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/insights'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['insights'] ?? [];
      }
    } catch (e) {
      print('获取见解失败: $e');
    }
    return [];
  }
}
```

## 🌐 跨域配置

如果遇到跨域问题，确保后端已正确配置CORS：

```python
# 在FastAPI中
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📊 错误处理

```javascript
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API调用失败:', error);
        throw error;
    }
}

// 使用示例
try {
    const insights = await apiCall(`${API_BASE}/insights`);
    console.log('见解:', insights);
} catch (error) {
    // 处理错误
    showErrorMessage(error.message);
}
```

## 🧪 测试API

### 使用cURL测试
```bash
# 健康检查
curl http://localhost:3001/api/v1/health

# 获取见解列表
curl http://localhost:3001/api/v1/insights

# 用户登录
curl -X POST http://localhost:3001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### 使用Postman
1. 导入API文档: `http://localhost:3001/openapi.json`
2. 设置环境变量: `API_BASE = http://localhost:3001/api/v1`
3. 测试各个端点

## 🚀 部署注意事项

### 生产环境
- 更新API基础URL为生产地址
- 配置HTTPS
- 设置正确的CORS域名
- 实现适当的错误处理和重试机制

### 环境变量
```javascript
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:3001/api/v1';
```

## 📚 完整示例

查看 `frontend-example/index.html` 文件，这是一个完整的前端集成示例，包含所有主要功能的演示。

## 🆘 常见问题

1. **CORS错误**: 检查后端CORS配置
2. **认证失败**: 确认Token格式和过期时间
3. **网络错误**: 检查API地址和网络连接
4. **数据格式**: 确认请求和响应的数据格式

---

**需要帮助？** 查看API文档: `http://localhost:3001/api/v1/docs`

