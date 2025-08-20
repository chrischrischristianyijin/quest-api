from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 导入路由
from app.routers import auth, user, insights, user_tags, metadata
from app.core.config import settings
from app.core.database import init_supabase

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    print("🚀 Starting Quest API...")
    await init_supabase()
    print("✅ Quest API started successfully")
    yield
    # 关闭时清理
    print("🔄 Shutting down Quest API...")

# 创建FastAPI应用
app = FastAPI(
    title="Quest API",
    description="一个用于收集和分享见解的平台API",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan
)

# 中间件配置 - 修复CORS问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
    ],
    expose_headers=["*"],
    max_age=86400,  # 预检请求缓存24小时
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # 生产环境应该限制具体域名
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(user.router, prefix="/api/v1/user", tags=["用户"])
app.include_router(insights.router, prefix="/api/v1/insights", tags=["见解"])
app.include_router(user_tags.router, prefix="/api/v1/user-tags", tags=["用户标签"])
app.include_router(metadata.router, prefix="/api/v1/metadata", tags=["元数据"])

@app.get("/api/v1/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "timestamp": "2024-01-01T00:00:00.000Z",
        "environment": os.getenv("NODE_ENV", "development"),
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Quest API",
        "version": "1.0.0",
        "docs": "/api/v1/docs"
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "statusCode": exc.status_code
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )
