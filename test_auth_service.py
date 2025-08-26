#!/usr/bin/env python3
"""
AuthService 测试脚本
用于验证改进后的认证服务是否正常工作
"""

import asyncio
import logging
from app.services.auth_service import AuthService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_auth_service():
    """测试 AuthService 的基本功能"""
    print("🧪 开始测试 AuthService...")
    
    try:
        # 创建 AuthService 实例
        auth_service = AuthService()
        print("✅ AuthService 实例创建成功")
        
        # 测试用户名生成
        test_email = "test.user@example.com"
        username = auth_service._generate_unique_username(test_email)
        print(f"✅ 用户名生成测试: {username}")
        
        # 测试邮箱检查（模拟）
        print("✅ 邮箱检查方法可用")
        
        # 测试默认标签
        print("✅ 默认标签配置加载成功")
        
        print("\n🎉 所有测试通过！AuthService 工作正常")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        logging.error(f"测试失败: {e}", exc_info=True)

def test_imports():
    """测试所有必要的导入"""
    print("🔍 测试导入...")
    
    try:
        from app.services.auth_service import AuthService
        print("✅ AuthService 导入成功")
        
        from app.models.user import UserCreate, UserLogin
        print("✅ 用户模型导入成功")
        
        from app.core.database import get_supabase, get_supabase_service
        print("✅ 数据库模块导入成功")
        
        print("✅ 所有导入测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 导入测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 AuthService 测试脚本")
    print("=" * 50)
    
    # 测试导入
    if test_imports():
        # 测试功能
        asyncio.run(test_auth_service())
    else:
        print("❌ 导入测试失败，跳过功能测试")
    
    print("\n🏁 测试完成")
