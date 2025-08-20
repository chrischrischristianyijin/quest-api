#!/usr/bin/env python3
"""
Quest API 测试示例脚本
演示各种API端点的输入输出格式
"""

import requests
import json

# API基础URL
BASE_URL = "http://localhost:3001/api/v1"

def test_health_check():
    """测试健康检查端点"""
    print("🔍 测试健康检查端点...")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_api_info():
    """测试API信息端点"""
    print("🔍 测试API信息端点...")
    
    response = requests.get(f"{BASE_URL}/")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_user_registration():
    """测试用户注册"""
    print("🔍 测试用户注册...")
    
    # 输入数据
    user_data = {
        "email": "test_api@example.com",
        "password": "testpassword123",
        "nickname": "API测试用户",
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    print(f"输入数据: {json.dumps(user_data, indent=2, ensure_ascii=False)}")
    
    response = requests.post(f"{BASE_URL}/auth/signup", json=user_data)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print(f"成功响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    print()

def test_user_login():
    """测试用户登录"""
    print("🔍 测试用户登录...")
    
    # 输入数据
    login_data = {
        "email": "test_api@example.com",
        "password": "testpassword123"
    }
    
    print(f"输入数据: {json.dumps(login_data, indent=2, ensure_ascii=False)}")
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"成功响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # 保存token用于后续测试
        if result.get("success") and result.get("data", {}).get("access_token"):
            return result["data"]["access_token"]
    else:
        print(f"错误响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    print()
    return None

def test_get_profile(access_token):
    """测试获取用户资料"""
    if not access_token:
        print("❌ 没有访问令牌，跳过用户资料测试")
        return
    
    print("🔍 测试获取用户资料...")
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    print(f"请求头: {json.dumps(headers, indent=2, ensure_ascii=False)}")
    
    response = requests.get(f"{BASE_URL}/auth/profile", headers=headers)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print(f"成功响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    print()

def test_check_email():
    """测试检查邮箱是否存在"""
    print("🔍 测试检查邮箱是否存在...")
    
    email = "test_api@example.com"
    print(f"查询参数: email={email}")
    
    response = requests.post(f"{BASE_URL}/auth/check-email?email={email}")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print(f"成功响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    print()

def test_google_login():
    """测试Google登录端点"""
    print("🔍 测试Google登录端点...")
    
    response = requests.get(f"{BASE_URL}/auth/google/login")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        print(f"成功响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    print()

def test_error_handling():
    """测试错误处理"""
    print("🔍 测试错误处理...")
    
    # 测试无效的登录数据
    invalid_login = {
        "email": "invalid@example.com",
        "password": "wrongpassword"
    }
    
    print(f"输入数据: {json.dumps(invalid_login, indent=2, ensure_ascii=False)}")
    
    response = requests.post(f"{BASE_URL}/auth/login", json=invalid_login)
    print(f"状态码: {response.status_code}")
    print(f"错误响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    print()

def main():
    """主函数"""
    print("🚀 Quest API 测试示例")
    print("=" * 50)
    
    try:
        # 基础端点测试
        test_health_check()
        test_api_info()
        
        # 用户认证测试
        test_user_registration()
        access_token = test_user_login()
        
        # 需要认证的端点测试
        if access_token:
            test_get_profile(access_token)
        
        # 其他端点测试
        test_check_email()
        test_google_login()
        
        # 错误处理测试
        test_error_handling()
        
        print("✅ 所有测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务器，请确保服务器正在运行")
        print("💡 运行命令: python3 main.py")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()
