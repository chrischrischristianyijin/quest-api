# Quest API - Python版本

一个使用Python FastAPI框架重构的Quest API后端服务，完全兼容原有的Node.js版本功能。

## 🚀 特性

- **FastAPI框架**: 现代化的Python Web框架，性能优异
- **异步支持**: 全异步设计，高并发处理
- **自动文档**: 自动生成OpenAPI文档
- **类型提示**: 完整的Python类型注解
- **Supabase集成**: 使用Supabase作为后端服务
- **JWT认证**: 安全的JWT令牌认证机制
- **完全兼容**: 与原有Node.js版本API接口完全一致

## 🏗️ 项目结构

```
quest-api/
├── app/                    # 应用主目录
│   ├── core/              # 核心配置
│   │   ├── config.py      # 配置管理
│   │   └── database.py    # 数据库连接
│   ├── models/            # 数据模型
│   │   └── user.py        # 用户模型
│   ├── routers/           # 路由定义
│   │   ├── auth.py        # 认证路由
│   │   ├── user.py        # 用户路由
│   │   ├── insights.py    # 见解路由
│   │   ├── user_tags.py   # 用户标签路由
│   │   └── metadata.py    # 元数据路由
│   ├── services/          # 业务逻辑
│   │   ├── auth_service.py # 认证服务
│   │   └── user_service.py # 用户服务
│   └── utils/             # 工具函数
├── supabase/              # 数据库配置
├── main.py                # 主应用入口
├── run.py                 # 启动脚本
├── requirements.txt       # Python依赖
└── README.md             # 项目说明
```

## 🛠️ 技术栈

- **Python 3.8+** - 运行环境
- **FastAPI** - Web框架
- **Uvicorn** - ASGI服务器
- **Pydantic** - 数据验证
- **Supabase** - 数据库和认证
- **JWT** - 身份认证
- **Passlib** - 密码哈希

## 📦 安装

### 1. 安装Python依赖

```bash
# 安装依赖
pip install -r requirements.txt

# 或者使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
NODE_ENV=development
API_PORT=3001
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
JWT_SECRET_KEY=your_jwt_secret_key
```

## 🚀 启动

### 方式1: 使用启动脚本

```bash
python run.py
```

### 方式2: 直接运行

```bash
python main.py
```

### 方式3: 使用uvicorn

```bash
uvicorn main:app --host 0.0.0.0 --port 3001 --reload
```

## 📚 API文档

启动服务后，访问以下地址查看API文档：

- **Swagger UI**: http://localhost:3001/api/v1/docs
- **ReDoc**: http://localhost:3001/api/v1/redoc
- **健康检查**: http://localhost:3001/api/v1/health

## 🔌 API端点

### 认证相关 (`/api/v1/auth`)

- `POST /register` - 用户注册
- `POST /login` - 用户登录
- `POST /signout` - 用户登出
- `POST /check-email` - 检查邮箱
- `GET /profile` - 获取当前用户
- `POST /forgot-password` - 忘记密码

### 用户相关 (`/api/v1/user`)

- `GET /profile/{email}` - 获取用户资料
- `PUT /profile/{email}` - 更新用户资料
- `POST /upload-avatar` - 上传头像
- `GET /followers/{email}` - 获取粉丝
- `GET /following/{email}` - 获取关注
- `POST /follow` - 关注用户
- `DELETE /follow` - 取消关注
- `GET /follow-status` - 关注状态

### 见解相关 (`/api/v1/insights`)

- `GET /` - 获取见解列表
- `GET /{id}` - 获取单个见解
- `POST /` - 创建见解
- `PUT /{id}` - 更新见解
- `DELETE /{id}` - 删除见解

### 用户标签 (`/api/v1/user-tags`)

- `GET /` - 获取用户标签
- `POST /` - 创建标签
- `PUT /{tag_id}` - 更新标签
- `DELETE /{tag_id}` - 删除标签
- `GET /stats` - 标签统计

### 元数据 (`/api/v1/metadata`)

- `GET /` - 获取系统元数据

## 🌟 Python版本优势

### 相比Node.js版本的优势

1. **性能提升**: FastAPI基于Starlette，性能接近Node.js
2. **类型安全**: 完整的Python类型提示，减少运行时错误
3. **自动文档**: 自动生成OpenAPI文档，无需手动维护
4. **开发体验**: 更好的IDE支持，代码补全和错误检查
5. **生态系统**: 丰富的Python数据科学和AI库
6. **团队协作**: Python在团队开发中更容易维护

## 🔧 开发

### 代码规范

- 使用Python类型提示
- 遵循PEP 8代码风格
- 异步函数使用async/await
- 完整的错误处理和日志记录

### 部署

```bash
# 生产环境启动
uvicorn main:app --host 0.0.0.0 --port 80 --workers 4

# Docker部署
docker build -t quest-api-python .
docker run -p 3001:3001 quest-api-python
```

## 📊 监控和日志

- 内置日志系统
- 健康检查端点
- 性能监控支持
- 错误追踪

## 🤝 贡献

欢迎提交Issue和Pull Request！

## �� 许可证

MIT License
