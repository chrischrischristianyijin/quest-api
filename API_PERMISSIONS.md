# 🔐 Quest API 权限控制说明

## 📋 权限控制原则

Quest API 采用基于用户ID的权限控制机制，确保用户只能访问和操作自己的数据。

## 🎯 核心权限规则

### 1. **用户认证要求**
- 除了健康检查和API信息端点，所有API都需要有效的JWT token
- Token通过 `Authorization: Bearer {token}` 头部传递

### 2. **数据隔离原则**
- 用户只能访问自己的数据（insights、tags、profile等）
- 即使指定了其他用户的ID，系统也会自动限制为当前登录用户

### 3. **权限检查机制**
- **列表查询**: 自动限制为当前用户的数据
- **单个资源**: 验证资源所有者是否为当前用户
- **创建/更新/删除**: 自动关联到当前用户

## 🔍 具体API权限说明

### **Insights API**

#### 获取insights列表
```http
GET /api/v1/insights?user_id=xxx
```
**权限逻辑：**
- 如果指定 `user_id`，只能查看自己的insights
- 如果不指定 `user_id`，默认查看当前登录用户的insights
- 系统会自动验证 `user_id` 是否为当前用户

#### 获取单个insight
```http
GET /api/v1/insights/{insight_id}
```
**权限逻辑：**
- 用户只能访问自己的insights
- 如果尝试访问其他用户的insight，返回403错误
- 系统会检查 `insight.user_id == current_user.id`

#### 创建insight
```http
POST /api/v1/insights
```
**权限逻辑：**
- 自动将 `user_id` 设置为当前登录用户
- 无需在请求体中指定 `user_id`

#### 更新insight
```http
PUT /api/v1/insights/{insight_id}
```
**权限逻辑：**
- 只能更新自己的insights
- 系统会验证insight的所有权

#### 删除insight
```http
DELETE /api/v1/insights/{insight_id}
```
**权限逻辑：**
- 只能删除自己的insights
- 系统会验证insight的所有权

### **User Tags API**

#### 获取标签列表
```http
GET /api/v1/user-tags?user_id=xxx
```
**权限逻辑：**
- 如果指定 `user_id`，只能查看自己的标签
- 如果不指定 `user_id`，默认查看当前登录用户的标签
- 系统会自动验证 `user_id` 是否为当前用户

#### 创建标签
```http
POST /api/v1/user-tags
```
**权限逻辑：**
- 自动将 `user_id` 设置为当前登录用户
- 无需在请求体中指定 `user_id`

#### 更新/删除标签
```http
PUT /api/v1/user-tags/{tag_id}
DELETE /api/v1/user-tags/{tag_id}
```
**权限逻辑：**
- 只能操作自己的标签
- 系统会验证标签的所有权

### **User Profile API**

#### 获取/更新用户资料
```http
GET /api/v1/user/profile
PUT /api/v1/user/profile
```
**权限逻辑：**
- 只能访问和修改自己的资料
- 系统自动使用当前登录用户的ID

## 🚫 权限错误响应

### 403 Forbidden
```json
{
  "success": false,
  "message": "无权限访问此insight",
  "statusCode": 403
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "message": "无效的认证token",
  "statusCode": 401
}
```

## 🔧 权限检查实现

### 1. **自动用户ID设置**
```python
# 在创建资源时自动设置用户ID
result = await service.create_resource(data, current_user["id"])
```

### 2. **所有权验证**
```python
# 在访问单个资源时验证所有权
if resource.user_id != current_user["id"]:
    raise HTTPException(status_code=403, detail="无权限访问")
```

### 3. **列表查询过滤**
```python
# 在查询列表时自动过滤用户数据
user_id = user_id or current_user["id"]
result = await service.get_resources(user_id=user_id)
```

## 📱 前端集成建议

### 1. **Token管理**
```javascript
// 在localStorage中保存token
localStorage.setItem('access_token', token);

// 在请求头中添加token
headers: {
  'Authorization': `Bearer ${localStorage.getItem('access_token')}`
}
```

### 2. **错误处理**
```javascript
// 处理权限错误
if (response.status === 403) {
  console.log('无权限访问此资源');
  // 重定向到登录页面或显示错误信息
}
```

### 3. **用户数据隔离**
```javascript
// 前端不需要指定user_id，系统会自动使用当前用户
const response = await fetch('/api/v1/insights', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

## 🎯 总结

Quest API 的权限控制系统确保：

✅ **数据安全** - 用户只能访问自己的数据  
✅ **自动隔离** - 无需手动指定用户ID  
✅ **统一验证** - 所有操作都经过权限检查  
✅ **清晰错误** - 权限错误有明确的错误信息  

这种设计既保证了安全性，又简化了前端集成！🔒
