from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """应用配置类"""
    
    # API配置
    API_PORT: int = 8080
    API_VERSION: str = "v1"
    
    # 环境配置
    NODE_ENV: str = "development"
    
    # CORS配置
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
    
    # Supabase配置
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    
    # JWT配置
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # 数据库配置
    DATABASE_URL: str = ""
    
    # 文件上传配置
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "./uploads"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建全局设置实例
settings = Settings()

# 从环境变量更新CORS配置
if os.getenv("ALLOWED_ORIGINS"):
    settings.ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS").split(",")
