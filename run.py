#!/usr/bin/env python3
"""
Quest API Python版本启动脚本
"""

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print("🚀 启动Quest API Python版本...")
    print(f"📡 端口: {settings.API_PORT}")
    print(f"🌐 环境: {settings.NODE_ENV}")
    print(f"🔗 文档: http://localhost:{settings.API_PORT}/api/v1/docs")
    print(f"💚 健康检查: http://localhost:{settings.API_PORT}/api/v1/health")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )
