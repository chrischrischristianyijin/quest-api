#!/usr/bin/env python3
"""
测试身份验证修复的脚本
"""
import asyncio
import httpx
import json
import os
from typing import Dict, Any

# 配置
BASE_URL = "http://localhost:8000"  # 根据实际部署调整
TEST_MESSAGES = [
    "hello",
    "What is artificial intelligence?",
    "How does machine learning work?",
    "Tell me about Python programming"
]

async def test_chat_without_auth():
    """测试无身份验证的聊天请求"""
    print("🧪 测试无身份验证的聊天请求...")
    
    async with httpx.AsyncClient() as client:
        for message in TEST_MESSAGES:
            try:
                payload = {
                    "message": message
                }
                
                response = await client.post(
                    f"{BASE_URL}/api/v1/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                
                print(f"✅ 请求: '{message}'")
                print(f"   状态码: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if "data" in data and "response" in data["data"]:
                            response_text = data["data"]["response"]
                            sources_count = len(data["data"].get("sources", []))
                            print(f"   响应: {response_text[:100]}...")
                            print(f"   来源数量: {sources_count}")
                        else:
                            print(f"   响应数据: {data}")
                    except json.JSONDecodeError:
                        print(f"   响应文本: {response.text[:200]}...")
                else:
                    print(f"   ❌ 错误: {response.text}")
                    
                print()
                
            except Exception as e:
                print(f"❌ 请求失败: {e}")
                print()

async def test_chat_with_fake_token():
    """测试使用假token的聊天请求"""
    print("🧪 测试使用假token的聊天请求...")
    
    # 测试不同类型的假token
    test_tokens = [
        "fake_token_123",
        "google_existing_user_test_user_12345",
        "google_new_user_test_user_67890", 
        "google_auth_token_test_user_11111",
        "test_user:fake_token"
    ]
    
    async with httpx.AsyncClient() as client:
        for token in test_tokens:
            try:
                payload = {
                    "message": "Hello with token"
                }
                
                response = await client.post(
                    f"{BASE_URL}/api/v1/chat",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}"
                    },
                    timeout=30.0
                )
                
                print(f"✅ Token: '{token[:30]}...'")
                print(f"   状态码: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if "data" in data and "response" in data["data"]:
                            response_text = data["data"]["response"]
                            sources_count = len(data["data"].get("sources", []))
                            print(f"   响应: {response_text[:100]}...")
                            print(f"   来源数量: {sources_count}")
                        else:
                            print(f"   响应数据: {data}")
                    except json.JSONDecodeError:
                        print(f"   响应文本: {response.text[:200]}...")
                else:
                    print(f"   ❌ 错误: {response.text}")
                    
                print()
                
            except Exception as e:
                print(f"❌ 请求失败: {e}")
                print()

async def test_health_check():
    """测试健康检查端点"""
    print("🧪 测试健康检查...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/v1/chat/health", timeout=10.0)
            print(f"✅ 健康检查状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   状态: {data.get('status')}")
                print(f"   消息: {data.get('message')}")
                if 'features' in data:
                    print(f"   功能: {data['features']}")
            else:
                print(f"   ❌ 错误: {response.text}")
                
        except Exception as e:
            print(f"❌ 健康检查失败: {e}")

async def main():
    """主测试函数"""
    print("🚀 开始测试身份验证修复...")
    print(f"📍 目标服务器: {BASE_URL}")
    print("=" * 60)
    
    # 测试健康检查
    await test_health_check()
    print()
    
    # 测试无身份验证的聊天
    await test_chat_without_auth()
    print()
    
    # 测试使用假token的聊天
    await test_chat_with_fake_token()
    print()
    
    print("🎉 测试完成!")

if __name__ == "__main__":
    asyncio.run(main())
