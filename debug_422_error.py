#!/usr/bin/env python3
"""
HTTP 422错误调试脚本
诊断创建insight时的数据验证问题
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# 配置
BASE_URL = "http://localhost:8000/api/v1"
TEST_URL = "https://www.python.org/"

async def test_metadata_create_insight():
    """测试metadata/create-insight端点"""
    print("🔍 测试 metadata/create-insight 端点...")
    print("=" * 60)
    
    # 测试数据
    test_cases = [
        {
            "name": "基本URL",
            "data": {"url": TEST_URL}
        },
        {
            "name": "带标题",
            "data": {"url": TEST_URL, "title": "Python官网"}
        },
        {
            "name": "带描述",
            "data": {"url": TEST_URL, "description": "Python编程语言官网"}
        },
        {
            "name": "带标签",
            "data": {"url": TEST_URL, "tags": "Python,编程,官网"}
        },
        {
            "name": "完整数据",
            "data": {
                "url": TEST_URL,
                "title": "Python官网",
                "description": "Python编程语言官网",
                "tags": "Python,编程,官网"
            }
        }
    ]
    
    async with httpx.AsyncClient() as client:
        for test_case in test_cases:
            print(f"\n🧪 测试: {test_case['name']}")
            print(f"数据: {test_case['data']}")
            
            try:
                # 使用FormData格式
                response = await client.post(
                    f"{BASE_URL}/metadata/create-insight",
                    data=test_case['data']
                )
                
                print(f"状态码: {response.status_code}")
                if response.status_code == 200:
                    print("✅ 成功")
                    data = response.json()
                    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                elif response.status_code == 422:
                    print("❌ 422错误 - 数据验证失败")
                    error_data = response.json()
                    print(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                else:
                    print(f"❌ 其他错误: {response.text}")
                    
            except Exception as e:
                print(f"❌ 请求异常: {e}")

async def test_insights_create():
    """测试insights创建端点"""
    print("\n🔍 测试 insights 创建端点...")
    print("=" * 60)
    
    # 测试数据
    test_cases = [
        {
            "name": "基本数据",
            "data": {
                "title": "测试insight",
                "description": "这是一个测试"
            }
        },
        {
            "name": "带URL",
            "data": {
                "title": "测试insight",
                "description": "这是一个测试",
                "url": TEST_URL
            }
        },
        {
            "name": "带图片",
            "data": {
                "title": "测试insight",
                "description": "这是一个测试",
                "image_url": "https://example.com/image.jpg"
            }
        },
        {
            "name": "带标签",
            "data": {
                "title": "测试insight",
                "description": "这是一个测试",
                "tag_names": ["测试", "示例"]
            }
        },
        {
            "name": "完整数据",
            "data": {
                "title": "测试insight",
                "description": "这是一个测试",
                "url": TEST_URL,
                "image_url": "https://example.com/image.jpg",
                "tag_names": ["测试", "示例"]
            }
        }
    ]
    
    async with httpx.AsyncClient() as client:
        for test_case in test_cases:
            print(f"\n🧪 测试: {test_case['name']}")
            print(f"数据: {test_case['data']}")
            
            try:
                response = await client.post(
                    f"{BASE_URL}/insights",
                    json=test_case['data']
                )
                
                print(f"状态码: {response.status_code}")
                if response.status_code == 200:
                    print("✅ 成功")
                    data = response.json()
                    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
                elif response.status_code == 422:
                    print("❌ 422错误 - 数据验证失败")
                    error_data = response.json()
                    print(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                else:
                    print(f"❌ 其他错误: {response.text}")
                    
            except Exception as e:
                print(f"❌ 请求异常: {e}")

async def test_model_validation():
    """测试Pydantic模型验证"""
    print("\n🔍 测试Pydantic模型验证...")
    print("=" * 60)
    
    try:
        from app.models.insight import InsightCreate
        
        # 测试有效数据
        valid_data = {
            "title": "测试标题",
            "description": "测试描述",
            "url": "https://example.com",
            "image_url": "https://example.com/image.jpg",
            "tag_names": ["测试", "示例"]
        }
        
        print("🧪 测试有效数据:")
        print(f"数据: {valid_data}")
        
        try:
            insight = InsightCreate(**valid_data)
            print("✅ 模型验证通过")
            print(f"验证后的数据: {insight.dict()}")
        except Exception as e:
            print(f"❌ 模型验证失败: {e}")
        
        # 测试无效数据
        invalid_cases = [
            {
                "name": "缺少标题",
                "data": {"description": "测试描述"}
            },
            {
                "name": "标题为空",
                "data": {"title": "", "description": "测试描述"}
            },
            {
                "name": "标题过长",
                "data": {"title": "a" * 201, "description": "测试描述"}
            },
            {
                "name": "描述过长",
                "data": {"title": "测试标题", "description": "a" * 1001}
            }
        ]
        
        for test_case in invalid_cases:
            print(f"\n🧪 测试无效数据: {test_case['name']}")
            print(f"数据: {test_case['data']}")
            
            try:
                insight = InsightCreate(**test_case['data'])
                print("⚠️  意外通过验证")
            except Exception as e:
                print(f"✅ 正确捕获验证错误: {e}")
                
    except ImportError as e:
        print(f"❌ 无法导入模型: {e}")

async def check_api_endpoints():
    """检查API端点"""
    print("\n🔍 检查API端点...")
    print("=" * 60)
    
    endpoints = [
        "/metadata/create-insight",
        "/insights",
        "/metadata/extract",
        "/metadata/preview"
    ]
    
    async with httpx.AsyncClient() as client:
        for endpoint in endpoints:
            try:
                response = await client.get(f"{BASE_URL}{endpoint}")
                print(f"✅ {endpoint}: {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint}: {e}")

async def main():
    """主函数"""
    print("🚀 HTTP 422错误调试工具")
    print("=" * 60)
    
    # 检查API端点
    await check_api_endpoints()
    
    # 测试模型验证
    await test_model_validation()
    
    # 测试metadata/create-insight端点
    await test_metadata_create_insight()
    
    # 测试insights创建端点
    await test_insights_create()
    
    print("\n" + "=" * 60)
    print("🎯 调试完成！")
    
    print("\n💡 常见422错误原因:")
    print("1. 缺少必需字段（如title）")
    print("2. 字段值不符合验证规则（长度、格式等）")
    print("3. 数据类型不匹配")
    print("4. 请求格式错误（JSON vs FormData）")
    print("5. 模型定义问题")

if __name__ == "__main__":
    asyncio.run(main())
