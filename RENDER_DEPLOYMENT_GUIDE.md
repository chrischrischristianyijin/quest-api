# Render 部署配置指南

## 🚀 部署步骤

### 1. 准备 Google OAuth 配置

在部署到 Render 之前，您需要：

1. **在 Google Cloud Console 中更新重定向 URI**
   - 访问 [Google Cloud Console](https://console.cloud.google.com/)
   - 选择您的项目
   - 进入 "API 和服务" > "凭据"
   - 编辑您的 OAuth 2.0 客户端
   - 在"已获授权的重定向 URI"中添加：
     ```
     https://your-app-name.onrender.com/api/v1/auth/google/callback
     ```
   - 将 `your-app-name` 替换为您在 Render 中的实际应用名称

### 2. 配置方式选择

您有两种方式在 Render 上配置环境变量：

#### 方式一：通过 render.yaml（推荐）

✅ **已更新的 render.yaml 文件**

您的 `render.yaml` 文件已经包含了 Google OAuth 的环境变量配置：

```yaml
envVars:
  # ... 其他环境变量 ...
  - key: GOOGLE_CLIENT_ID
    value: your_google_client_id.apps.googleusercontent.com
  - key: GOOGLE_CLIENT_SECRET
    value: your_google_client_secret
  - key: GOOGLE_REDIRECT_URI
    value: https://your-app-name.onrender.com/api/v1/auth/google/callback
```

**需要更新的值：**
1. `your_google_client_id.apps.googleusercontent.com` → 您的实际 Google Client ID
2. `your_google_client_secret` → 您的实际 Google Client Secret
3. `your-app-name` → 您在 Render 中的应用名称

#### 方式二：通过 Render Dashboard

如果您不想在 YAML 文件中暴露敏感信息，可以在 Render Dashboard 中手动配置：

1. **登录 Render Dashboard**
   - 访问 [Render Dashboard](https://dashboard.render.com/)

2. **选择您的服务**
   - 找到您的 quest-api 服务

3. **添加环境变量**
   - 进入 "Environment" 选项卡
   - 点击 "Add Environment Variable"
   - 添加以下变量：

```
GOOGLE_CLIENT_ID = your_actual_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET = your_actual_client_secret
GOOGLE_REDIRECT_URI = https://your-app-name.onrender.com/api/v1/auth/google/callback
```

### 3. 重要配置提醒

#### 🔒 安全最佳实践

1. **敏感信息处理**
   - `GOOGLE_CLIENT_SECRET` 是敏感信息
   - 建议通过 Render Dashboard 手动配置，而不是写在 YAML 文件中
   - 从 `render.yaml` 中移除 `GOOGLE_CLIENT_SECRET` 并在 Dashboard 中配置

2. **更新 render.yaml（安全版本）**
   ```yaml
   envVars:
     # ... 其他变量 ...
     - key: GOOGLE_CLIENT_ID
       value: your_google_client_id.apps.googleusercontent.com
     - key: GOOGLE_REDIRECT_URI
       value: https://your-app-name.onrender.com/api/v1/auth/google/callback
     # 注意：GOOGLE_CLIENT_SECRET 应该在 Dashboard 中配置，不写在这里
   ```

#### 🌐 域名配置

1. **获取 Render 应用 URL**
   - 部署完成后，Render 会提供一个 URL，格式通常为：
     `https://your-app-name.onrender.com`

2. **更新所有相关配置**
   - Google Cloud Console 中的重定向 URI
   - `GOOGLE_REDIRECT_URI` 环境变量
   - `ALLOWED_ORIGINS` 环境变量（如果前端也部署在其他域名）

### 4. 部署流程

1. **推送代码到 GitHub**
   ```bash
   git add .
   git commit -m "Add Google OAuth configuration"
   git push origin main
   ```

2. **Render 自动部署**
   - 如果配置了 `autoDeploy: true`，Render 会自动开始部署
   - 您可以在 Render Dashboard 中查看部署日志

3. **验证部署**
   - 部署完成后，访问：`https://your-app-name.onrender.com/api/v1/auth/google/login`
   - 应该返回包含正确 OAuth URL 的 JSON 响应

### 5. 故障排除

#### 常见问题

1. **redirect_uri_mismatch 错误**
   - 检查 Google Console 中的重定向 URI 是否与 `GOOGLE_REDIRECT_URI` 完全匹配
   - 确保使用 HTTPS 协议

2. **Environment variable not found**
   - 确认所有环境变量都已在 Render 中正确配置
   - 检查变量名是否拼写正确

3. **CORS 错误**
   - 更新 `ALLOWED_ORIGINS` 包含您的前端域名
   - 确保前端使用正确的 API 域名

#### 调试命令

在 Render Dashboard 的 "Shell" 中运行：

```bash
# 检查环境变量是否正确加载
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_REDIRECT_URI

# 测试 API 端点
curl https://your-app-name.onrender.com/health
curl https://your-app-name.onrender.com/api/v1/auth/google/login
```

### 6. 生产环境清单

- [ ] Google Cloud Console 中配置了生产环境重定向 URI
- [ ] Render 中配置了所有必要的环境变量
- [ ] `GOOGLE_CLIENT_SECRET` 通过 Dashboard 安全配置
- [ ] `GOOGLE_REDIRECT_URI` 使用正确的生产域名
- [ ] `ALLOWED_ORIGINS` 包含前端生产域名
- [ ] 测试了完整的 OAuth 流程

### 7. 后续维护

1. **定期更新依赖**
   ```bash
   pip list --outdated
   pip install --upgrade package_name
   ```

2. **监控和日志**
   - 在 Render Dashboard 中查看应用日志
   - 监控 Google OAuth 使用情况

3. **安全更新**
   - 定期轮换 Client Secret
   - 监控异常登录活动
