# Chrome扩展 Google OAuth 配置指南

## 🎯 问题解决方案

您遇到的问题是Chrome扩展应该使用**Supabase原生的Google OAuth**，而不是自定义实现。

## 📋 配置步骤

### 1. Google Cloud Console 配置

1. **创建Chrome扩展OAuth客户端**
   - 访问 [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials)
   - 点击 "创建凭据" > "OAuth 2.0 客户端 ID"
   - **应用类型选择**: `Chrome扩展`
   - **Item ID**: 您的Chrome扩展ID（从`chrome.runtime.id`获取）

2. **配置OAuth同意屏幕**
   - 设置应用信息
   - 添加作用域: `openid`, `email`, `profile`

### 2. Supabase Dashboard 配置

1. **启用Google Provider**
   - 进入 Supabase Dashboard
   - Authentication > Providers > Google
   - 启用 "Enable sign in with Google"
   - 添加您的Chrome扩展Client ID到"Client IDs"列表

2. **重要**: 不需要在Supabase中配置OAuth flow，因为Chrome扩展使用原生流程

### 3. Chrome扩展 manifest.json 配置

```json
{
  "manifest_version": 3,
  "permissions": ["identity"],
  "oauth2": {
    "client_id": "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com",
    "scopes": ["openid", "email", "profile"]
  }
}
```

### 4. Chrome扩展前端代码

```javascript
// 获取Google ID Token
async function signInWithGoogle() {
  return new Promise((resolve, reject) => {
    const manifest = chrome.runtime.getManifest();
    const url = new URL('https://accounts.google.com/o/oauth2/auth');
    
    url.searchParams.set('client_id', manifest.oauth2.client_id);
    url.searchParams.set('response_type', 'id_token');
    url.searchParams.set('access_type', 'offline');
    url.searchParams.set('redirect_uri', `https://${chrome.runtime.id}.chromiumapp.org`);
    url.searchParams.set('scope', manifest.oauth2.scopes.join(' '));
    
    chrome.identity.launchWebAuthFlow(
      {
        url: url.href,
        interactive: true,
      },
      async (redirectedTo) => {
        if (chrome.runtime.lastError) {
          reject(chrome.runtime.lastError);
        } else {
          // 提取ID Token
          const url = new URL(redirectedTo);
          const params = new URLSearchParams(url.hash.substring(1));
          const idToken = params.get('id_token');
          
          if (idToken) {
            // 发送到您的API
            try {
              const response = await fetch('https://quest-api-edz1.onrender.com/api/v1/auth/google/token', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `id_token=${idToken}`
              });
              
              const result = await response.json();
              resolve(result);
            } catch (error) {
              reject(error);
            }
          } else {
            reject(new Error('未获取到ID Token'));
          }
        }
      }
    );
  });
}
```

## 🔧 后端API修复

### 修复的关键点

1. **使用Supabase原生方法**
   ```python
   # 新的实现
   auth_response = self.supabase.auth.sign_in_with_id_token({
       "provider": "google",
       "token": id_token_str
   })
   ```

2. **自动处理用户统一**
   - Supabase会自动识别相同邮箱的用户
   - 无论是email/password注册还是Google登录，相同邮箱会映射到同一个用户

3. **确保Profile一致性**
   ```python
   async def _ensure_user_profile(self, user) -> None:
       # 检查并创建profile记录
       # 确保Google登录和常规登录用户数据一致
   ```

## ✅ 解决的问题

### 之前的问题
- 用户先email/password注册，再Google登录时被当作新用户
- 界面显示不一致
- 数据重复

### 修复后的行为
- ✅ 相同邮箱自动识别为同一用户
- ✅ Google登录和email登录界面一致
- ✅ 用户数据统一管理
- ✅ 无重复账户

## 🧪 测试步骤

1. **测试现有用户Google登录**
   ```bash
   # 用真实的Google ID Token测试
   curl -X POST "https://quest-api-edz1.onrender.com/api/v1/auth/google/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "id_token=REAL_GOOGLE_ID_TOKEN"
   ```

2. **验证用户统一**
   - 先用email/password注册
   - 再用Google登录（相同邮箱）
   - 确认返回相同的用户ID

## 🔄 部署流程

1. **推送代码更改**
   ```bash
   git add .
   git commit -m "Fix Google OAuth using Supabase native integration"
   git push origin main
   ```

2. **配置环境变量**
   - 确保Render中有正确的Google配置
   - 验证Supabase配置

## 📈 预期结果

修复后，您的用户体验将是：

1. **新用户**: Google登录 → 创建account → 正常界面
2. **现有用户**: Google登录 → 识别现有account → 相同界面
3. **数据一致**: 无论哪种登录方式，用户看到相同的数据

这样就解决了"用google 登陆进入的页面跟正常email password的界面不一样"的问题！
