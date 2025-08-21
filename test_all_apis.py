#!/usr/bin/env python3
"""
Quest API 全面功能测试脚本
测试所有主要API端点是否正常工作
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# API基础URL
BASE_URL = "http://localhost:8000/api/v1"

class QuestAPITester:
    def __init__(self):
        self.access_token = None
        self.user_id = None
        self.test_user = {
            "email": "test@example.com",
            "password": "testpassword123",
            "nickname": "TestUser"
        }
    
    async def test_health_check(self):
        """测试健康检查"""
        print("🔍 测试健康检查...")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            print(f"健康检查状态: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 健康检查成功: {data}")
            else:
                print(f"❌ 健康检查失败: {response.text}")
    
    async def test_api_info(self):
        """测试API信息"""
        print("\n🔍 测试API信息...")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/")
            print(f"API信息状态: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API信息获取成功: {data}")
            else:
                print(f"❌ API信息获取失败: {response.text}")
    
    async def test_user_registration(self):
        """测试用户注册"""
        print("\n🔍 测试用户注册...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/auth/signup",
                json=self.test_user
            )
            print(f"用户注册状态: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 用户注册成功: {data}")
                # 保存用户ID和token用于后续测试
                if data.get("success") and data.get("data", {}).get("user"):
                    self.user_id = data["data"]["user"]["id"]
                    if data.get("data", {}).get("access_token"):
                        self.access_token = data["data"]["access_token"]
            else:
                print(f"❌ 用户注册失败: {response.text}")
    
    async def test_user_login(self):
        """测试用户登录"""
        print("\n🔍 测试用户登录...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": self.test_user["email"],
                    "password": self.test_user["password"]
                }
            )
            print(f"用户登录状态: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 用户登录成功: {data}")
                if data.get("success") and data.get("data", {}).get("access_token"):
                    self.access_token = data["data"]["access_token"]
                    if data.get("data", {}).get("user_id"):
                        self.user_id = data["data"]["user_id"]
            else:
                print(f"❌ 用户登录失败: {response.text}")
    
    async def test_get_user_profile(self):
        """测试获取用户资料"""
        if not self.access_token:
            print("❌ 需要先登录获取token")
            return
        
        print("\n🔍 测试获取用户资料...")
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await client.get(f"{BASE_URL}/auth/profile", headers=headers)
            print(f"获取用户资料状态: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 获取用户资料成功: {data}")
            else:
                print(f"❌ 获取用户资料失败: {response.text}")
    
    async def test_create_tag(self):
        """测试创建标签"""
        if not self.access_token:
            print("❌ 需要先登录获取token")
            return
        
        print("\n🔍 测试创建标签...")
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            tag_data = {
                "name": "测试标签",
                "color": "#FF5733"
            }
            response = await client.post(
                f"{BASE_URL}/user-tags",
                json=tag_data,
                headers=headers
            )
            print(f"创建标签状态: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 创建标签成功: {data}")
            else:
                print(f"❌ 创建标签失败: {response.text}")
    
    async def test_get_user_tags(self):
        """测试获取用户标签"""
        if not self.access_token:
            print("❌ 需要先登录获取token")
            return
        
        print("\n🔍 测试获取用户标签...")
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await client.get(f"{BASE_URL}/user-tags", headers=headers)
            print(f"获取用户标签状态: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 获取用户标签成功: {data}")
            else:
                print(f"❌ 获取用户标签失败: {response.text}")
    
    async def test_create_insight(self):
        """测试创建insight"""
        if not self.access_token:
            print("❌ 需要先登录获取token")
            return
        
        print("\n🔍 测试创建insight...")
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            insight_data = {
                "title": "测试insight",
                "description": "这是一个测试insight",
                "url": "https://example.com",
                "tags": ["测试", "示例"]
            }
            response = await client.post(
                f"{BASE_URL}/insights",
                json=insight_data,
                headers=headers
            )
            print(f"创建insight状态: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 创建insight成功: {data}")
            else:
                print(f"❌ 创建insight失败: {response.text}")
    
    async def test_get_insights(self):
        """测试获取insights"""
        if not self.access_token:
            print("❌ 需要先登录获取token")
            return
        
        print("\n🔍 测试获取insights...")
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await client.get(f"{BASE_URL}/insights", headers=headers)
            print(f"获取insights状态: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 获取insights成功: {data}")
            else:
                print(f"❌ 获取insights失败: {response.text}")
    
    async def test_metadata_extraction(self):
        """测试元数据提取"""
        print("\n🔍 测试元数据提取...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/metadata/extract",
                data={"url": "https://example.com"}
            )
            print(f"元数据提取状态: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 元数据提取成功: {data}")
            else:
                print(f"❌ 元数据提取失败: {response.text}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行Quest API全面功能测试...")
        print("=" * 50)
        
        try:
            # 基础功能测试
            await self.test_health_check()
            await self.test_api_info()
            
            # 用户认证测试
            await self.test_user_registration()
            await self.test_user_login()
            
            # 用户信息测试
            await self.test_get_user_profile()
            
            # 标签功能测试
            await self.test_create_tag()
            await self.test_get_user_tags()
            
            # Insight功能测试
            await self.test_create_insight()
            await self.test_get_insights()
            
            # 元数据功能测试
            await self.test_metadata_extraction()
            
            print("\n" + "=" * 50)
            print("🎉 所有测试完成！")
            
        except Exception as e:
            print(f"\n❌ 测试过程中出现错误: {e}")

async def main():
    """主函数"""
    tester = QuestAPITester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
