#!/usr/bin/env python3
"""
快速测试HTTP 422错误
"""

import requests
import json

def test_create_insight():
    """测试创建insight"""
    print("🔍 测试创建insight...")
    
    # 测试数据
    test_data = {
        "title": "测试insight",
        "description": "这是一个测试"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/insights",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("✅ 成功")
        elif response.status_code == 422:
            print("❌ 422错误 - 数据验证失败")
            print(f"错误详情: {response.text}")
        else:
            print(f"响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def test_metadata_create_insight():
    """测试metadata/create-insight"""
    print("\n🔍 测试metadata/create-insight...")
    
    # 测试数据
    test_data = {
        "url": "https://www.python.org/"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/metadata/create-insight",
            data=test_data
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("✅ 成功")
        elif response.status_code == 422:
            print("❌ 422错误 - 数据验证失败")
            print(f"错误详情: {response.text}")
        else:
            print(f"响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def test_metadata_extract():
    """测试metadata/extract"""
    print("\n🔍 测试metadata/extract...")
    
    # 测试数据
    test_data = {
        "url": "https://www.python.org/"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/metadata/extract",
            data=test_data
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print("✅ 成功")
        elif response.status_code == 422:
            print("❌ 422错误 - 数据验证失败")
            print(f"错误详情: {response.text}")
        else:
            print(f"响应: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def main():
    print("🚀 快速测试HTTP 422错误")
    print("=" * 50)
    
    # 测试各个端点
    test_create_insight()
    test_metadata_create_insight()
    test_metadata_extract()
    
    print("\n" + "=" * 50)
    print("🎯 测试完成！")

if __name__ == "__main__":
    main()
