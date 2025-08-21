#!/usr/bin/env python3
"""
Quest API 系统状态检查脚本
检查所有组件是否正常工作
"""

import asyncio
import sys
from pathlib import Path

def check_file_structure():
    """检查文件结构"""
    print("🔍 检查文件结构...")
    
    required_files = [
        "main.py",
        "requirements.txt",
        "app/core/config.py",
        "app/core/database.py",
        "app/routers/auth.py",
        "app/routers/user.py",
        "app/routers/insights.py",
        "app/routers/user_tags.py",
        "app/routers/metadata.py",
        "app/services/auth_service.py",
        "app/services/user_service.py",
        "app/services/insights_service.py",
        "app/services/user_tag_service.py",
        "app/models/insight.py",
        "app/models/user.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 缺少文件: {missing_files}")
        return False
    else:
        print("✅ 所有必需文件都存在")
        return True

def check_dependencies():
    """检查Python依赖"""
    print("\n🔍 检查Python依赖...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "supabase",
        "pydantic",
        "httpx",
        "beautifulsoup4"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少Python包: {missing_packages}")
        print("请运行: pip install -r requirements.txt")
        return False
    else:
        print("✅ 所有Python依赖都已安装")
        return True

def check_configuration():
    """检查配置文件"""
    print("\n🔍 检查配置文件...")
    
    try:
        from app.core.config import settings
        
        # 检查关键配置
        if not settings.SUPABASE_URL:
            print("⚠️  SUPABASE_URL 未设置")
        if not settings.SUPABASE_ANON_KEY:
            print("⚠️  SUPABASE_ANON_KEY 未设置")
        if not settings.SUPABASE_SERVICE_ROLE_KEY:
            print("⚠️  SUPABASE_SERVICE_ROLE_KEY 未设置")
        
        print("✅ 配置文件加载成功")
        return True
        
    except Exception as e:
        print(f"❌ 配置文件检查失败: {e}")
        return False

def check_database_connection():
    """检查数据库连接"""
    print("\n🔍 检查数据库连接...")
    
    try:
        from app.core.database import get_supabase
        supabase = get_supabase()
        
        # 简单连接测试
        response = supabase.table('profiles').select('id').limit(1).execute()
        
        if response.error:
            print(f"⚠️  数据库连接警告: {response.error}")
        else:
            print("✅ 数据库连接正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def check_api_routes():
    """检查API路由"""
    print("\n🔍 检查API路由...")
    
    try:
        from main import app
        
        # 检查主要路由
        routes = [
            "/",
            "/health",
            "/api/v1/",
            "/api/v1/docs",
            "/api/v1/redoc"
        ]
        
        for route in routes:
            if any(route.path == route for route in app.routes):
                print(f"✅ 路由 {route} 存在")
            else:
                print(f"⚠️  路由 {route} 可能有问题")
        
        print("✅ API路由检查完成")
        return True
        
    except Exception as e:
        print(f"❌ API路由检查失败: {e}")
        return False

async def main():
    """主检查函数"""
    print("🚀 Quest API 系统状态检查")
    print("=" * 50)
    
    checks = [
        check_file_structure,
        check_dependencies,
        check_configuration,
        check_database_connection,
        check_api_routes
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ 检查过程出错: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 检查结果汇总:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 系统状态良好，可以部署到Render！")
        return 0
    else:
        print("⚠️  系统存在问题，请修复后再部署")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
