#!/usr/bin/env python3
"""
测试Quest API的兼容性
"""

def test_imports():
    """测试所有关键导入"""
    print("🔍 测试关键组件导入...")
    
    try:
        # 测试Pydantic
        from pydantic import BaseModel, Field
        print("✅ Pydantic导入成功")
        
        # 测试FastAPI
        from fastapi import FastAPI
        print("✅ FastAPI导入成功")
        
        # 测试Supabase
        from supabase import create_client
        print("✅ Supabase导入成功")
        
        # 测试路由
        from app.routers import auth, user, insights, user_tags, metadata
        print("✅ 所有路由导入成功")
        
        # 测试服务
        from app.services import insights_service, user_tag_service, user_service, auth_service
        print("✅ 所有服务导入成功")
        
        # 测试模型
        from app.models import insight, user
        print("✅ 所有模型导入成功")
        
        # 测试配置
        from app.core import config, database
        print("✅ 配置和数据库模块导入成功")
        
        print("\n🎉 所有组件导入成功！")
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_pydantic_models():
    """测试Pydantic模型"""
    print("\n🔍 测试Pydantic模型...")
    
    try:
        from app.models.insight import InsightCreate, UserTagCreate
        from app.models.user import UserCreate
        
        # 测试创建模型实例
        insight_data = {
            "title": "测试见解",
            "description": "这是一个测试",
            "tag_names": ["测试", "示例"]
        }
        insight = InsightCreate(**insight_data)
        print("✅ InsightCreate模型测试成功")
        
        tag_data = {
            "name": "测试标签",
            "color": "#FF5733"
        }
        tag = UserTagCreate(**tag_data)
        print("✅ UserTagCreate模型测试成功")
        
        user_data = {
            "email": "test@example.com",
            "nickname": "测试用户",
            "password": "password123"
        }
        user = UserCreate(**user_data)
        print("✅ UserCreate模型测试成功")
        
        print("🎉 所有Pydantic模型测试成功！")
        return True
        
    except Exception as e:
        print(f"❌ 模型测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 Quest API 兼容性测试")
    print("=" * 50)
    
    # 测试导入
    imports_ok = test_imports()
    
    # 测试模型
    models_ok = test_pydantic_models()
    
    if imports_ok and models_ok:
        print("\n🎉 所有测试通过！系统兼容性良好。")
    else:
        print("\n❌ 部分测试失败，请检查错误信息。")

if __name__ == "__main__":
    main()
