# 🎯 Chrome扩展OAuth精确修复方案

## 确认信息
- **Chrome扩展ID**: `jcjpicpelibofggpbbmajafjipppnojo`
- **后端客户端ID**: `103202343935-5dkesvf5dp06af09o0d2373ji2ccd0rc.apps.googleusercontent.com`

## 🔧 修复方案A: 配置现有客户端支持Chrome扩展

### 步骤1: 更新Google Cloud Console

1. **访问 [Google Cloud Console](https://console.cloud.google.com/)**

2. **进入 "API 和服务" > "凭据"**

3. **找到并编辑客户端ID**: `103202343935-5dkesvf5dp06af09o0d2373ji2ccd0rc`

4. **修改应用类型**:
   - 如果当前是"Web应用程序"，需要同时支持Chrome扩展
   - 可能需要创建一个新的OAuth客户端专门用于Chrome扩展

### 步骤2: 创建Chrome扩展专用OAuth客户端（推荐）

1. **创建新的OAuth客户端**:
   - 点击 "创建凭据" > "OAuth客户端ID"
   - **应用类型**: 选择 "Chrome扩展程序"
   - **Item ID**: 输入 `jcjpicpelibofggpbbmajafjipppnojo`
   - 点击创建

2. **记录新的客户端ID** (会类似这样):
   ```
   新客户端ID-chrome.apps.googleusercontent.com
   ```

### 步骤3: 更新Chrome扩展manifest.json

有两个选择：

**选择A: 使用现有客户端ID（如果Google Console支持）**
```json
{
  "manifest_version": 3,
  "name": "Quest Extension",
  "permissions": ["identity", "storage", "activeTab"],
  "oauth2": {
    "client_id": "103202343935-5dkesvf5dp06af09o0d2373ji2ccd0rc.apps.googleusercontent.com",
    "scopes": ["openid", "email", "profile"]
  },
  "host_permissions": ["https://quest-api-edz1.onrender.com/*"]
}
```

**选择B: 使用新的Chrome扩展专用客户端ID（推荐）**
```json
{
  "manifest_version": 3,
  "name": "Quest Extension", 
  "permissions": ["identity", "storage", "activeTab"],
  "oauth2": {
    "client_id": "新的Chrome扩展客户端ID.apps.googleusercontent.com",
    "scopes": ["openid", "email", "profile"]
  },
  "host_permissions": ["https://quest-api-edz1.onrender.com/*"]
}
```

## 🚀 修复方案B: 后端支持多个客户端ID（最佳）

如果您创建了Chrome扩展专用客户端，后端需要能够验证两个客户端ID的ID Token。

### 更新后端配置

修改 `app/core/config.py`:

```python
class Settings(BaseSettings):
    # 现有配置...
    GOOGLE_CLIENT_ID: str = ""  # Web应用客户端ID
    GOOGLE_CLIENT_ID_CHROME: str = ""  # Chrome扩展客户端ID
    
    # 或者使用列表支持多个客户端
    GOOGLE_ALLOWED_CLIENT_IDS: list = []
```

### 更新ID Token验证逻辑

修改 `app/services/auth_service.py` 中的 `google_token_login` 方法:

```python
async def google_token_login(self, id_token_str: str) -> dict:
    """使用Google ID Token登录 - 支持多个客户端ID"""
    try:
        # 支持的客户端ID列表
        allowed_client_ids = [
            settings.GOOGLE_CLIENT_ID,  # Web应用
            settings.GOOGLE_CLIENT_ID_CHROME,  # Chrome扩展
        ]
        allowed_client_ids = [cid for cid in allowed_client_ids if cid]  # 过滤空值
        
        id_info = None
        for client_id in allowed_client_ids:
            try:
                id_info = id_token.verify_oauth2_token(
                    id_token_str, 
                    requests.Request(), 
                    client_id
                )
                self.logger.info(f"ID Token验证成功，客户端: {client_id}")
                break
            except ValueError as e:
                self.logger.debug(f"客户端{client_id}验证失败: {e}")
                continue
        
        if not id_info:
            raise ValueError("无法验证ID Token - 所有客户端ID都失败")
            
        # 继续现有逻辑...
```

## 🎯 立即测试步骤

### 1. 测试当前配置

在Chrome扩展popup控制台中运行:

```javascript
// 检查配置
console.log('Extension ID:', chrome.runtime.id);
console.log('OAuth Config:', chrome.runtime.getManifest().oauth2);

// 测试OAuth流程
const manifest = chrome.runtime.getManifest();
const url = new URL('https://accounts.google.com/o/oauth2/auth');
url.searchParams.set('client_id', manifest.oauth2.client_id);
url.searchParams.set('response_type', 'id_token');
url.searchParams.set('redirect_uri', `https://${chrome.runtime.id}.chromiumapp.org/`);
url.searchParams.set('scope', manifest.oauth2.scopes.join(' '));

console.log('Test OAuth URL:', url.href);

// 尝试启动OAuth流程
chrome.identity.launchWebAuthFlow({
    url: url.href,
    interactive: true
}, (responseUrl) => {
    if (chrome.runtime.lastError) {
        console.error('OAuth Error:', chrome.runtime.lastError);
    } else {
        console.log('OAuth Success:', responseUrl);
    }
});
```

### 2. 验证Google Console配置

访问以下URL检查OAuth客户端是否正确配置:

```
https://accounts.google.com/o/oauth2/auth?client_id=103202343935-5dkesvf5dp06af09o0d2373ji2ccd0rc.apps.googleusercontent.com&response_type=id_token&redirect_uri=https://jcjpicpelibofggpbbmajafjipppnojo.chromiumapp.org/&scope=openid%20email%20profile
```

## 📋 下一步行动清单

请按顺序执行:

1. [ ] **在Google Cloud Console中为扩展ID `jcjpicpelibofggpbbmajafjipppnojo` 创建Chrome扩展OAuth客户端**

2. [ ] **记录新的Chrome扩展客户端ID**

3. [ ] **更新Chrome扩展manifest.json使用新客户端ID**

4. [ ] **测试Chrome扩展OAuth流程**

5. [ ] **如果成功，通知我新的客户端ID，我会更新后端支持**

## 🚨 最关键的问题

**当前问题**: Chrome扩展尝试使用Web应用的客户端ID，但Google不允许Chrome扩展使用Web应用的OAuth客户端。

**解决方案**: 必须在Google Cloud Console中创建专门的"Chrome扩展程序"类型OAuth客户端，并使用扩展ID `jcjpicpelibofggpbbmajafjipppnojo`。

请先完成Google Cloud Console的配置，然后告诉我新的客户端ID！
