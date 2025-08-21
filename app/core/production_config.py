"""
生产环境配置
用于Render等生产环境部署
"""

from app.core.config import settings
from typing import List

class ProductionSettings:
    """生产环境特定配置"""
    
    # 安全配置
    DEBUG: bool = False
    RELOAD: bool = False
    
    # CORS配置 - 生产环境应该限制具体域名
    ALLOWED_ORIGINS: List[str] = [
        "https://yourdomain.com",
        "https://www.yourdomain.com",
        "https://your-frontend-app.onrender.com"
    ]
    
    # 主机配置
    ALLOWED_HOSTS: List[str] = [
        "your-app-name.onrender.com",
        "yourdomain.com",
        "www.yourdomain.com"
    ]
    
    # 性能配置
    WORKERS: int = 1  # Render建议使用1个worker
    
    # 日志配置
    LOG_LEVEL: str = "info"
    
    # 安全头配置
    SECURITY_HEADERS: dict = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }

# 生产环境配置实例
production_settings = ProductionSettings()
