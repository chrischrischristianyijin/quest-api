#!/usr/bin/env python3
"""
生产环境启动脚本
用于Render等生产环境部署
"""

import os
import uvicorn
from app.core.config import settings

def main():
    """生产环境启动函数"""
    
    # 获取端口（Render会自动设置PORT环境变量）
    port = int(os.getenv("PORT", settings.API_PORT))
    
    # 生产环境配置
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # 生产环境禁用热重载
        workers=1,     # Render建议使用1个worker
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
