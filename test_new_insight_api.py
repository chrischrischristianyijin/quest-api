#!/usr/bin/env python3
"""
测试新的创建见解API（从URL自动获取metadata）
"""

import requests
import json
import sys

# API配置
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/v1/insights"

def test_create_insight_from_url():
    """测试从URL创建见解"""
    
    # 测试数据
    test_data = {
        "url": "https://www.nytimes.com/2025/07/14/us/politics/trump-putin-ukraine.html",
        "thought": "这是一个关于国际政治的新闻，值得关注",
        "tag_ids": [
            "550e8400-e29b-41d4-a716-446655440001",  # 政治标签ID
            "550e8400-e29b-41d4-a716-446655440002",  # 国际标签ID
            "550e8400-e29b-41d4-a716-446655440003"   # 新闻标签ID
        ]
    }
    
    print("🧪 测试创建见解API（从URL自动获取metadata）")
    print(f"📡 请求地址: {API_ENDPOINT}")
    print(f"📋 请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    
    try:
        # 发送请求
        response = requests.post(
            API_ENDPOINT,
            json=test_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer YOUR_TOKEN_HERE"  # 需要替换为实际的token
            },
            timeout=30
        )
        
        print(f"\n📊 响应状态码: {response.status_code}")
        print(f"📄 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 验证返回的数据
            if result.get("success"):
                data = result.get("data", {})
                print(f"\n🔍 验证返回数据:")
                print(f"  - ID: {data.get('id')}")
                print(f"  - URL: {data.get('url')}")
                print(f"  - 标题: {data.get('title')}")
                print(f"  - 描述: {data.get('description', '')[:100]}...")
                print(f"  - 图片: {data.get('image_url')}")
                print(f"  - 想法: {data.get('thought')}")
                print(f"  - 标签数量: {len(data.get('tags', []))}")
                
                if data.get('tags'):
                    print(f"  - 标签详情:")
                    for tag in data.get('tags', []):
                        print(f"    * {tag.get('name')} ({tag.get('color')})")
            else:
                print(f"❌ API返回失败: {result.get('message')}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
            except:
                print(f"错误内容: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
    except Exception as e:
        print(f"❌ 其他异常: {e}")

def test_metadata_extraction():
    """测试metadata提取功能"""
    print("\n🔍 测试metadata提取功能")
    
    # 这里可以添加单独的metadata提取测试
    # 如果后端有独立的metadata提取端点的话
    pass

if __name__ == "__main__":
    print("🚀 开始测试新的创建见解API")
    print("=" * 50)
    
    # 测试创建见解
    test_create_insight_from_url()
    
    # 测试metadata提取
    test_metadata_extraction()
    
    print("\n" + "=" * 50)
    print("🏁 测试完成")
    
    print("\n📝 使用说明:")
    print("1. 确保后端服务正在运行 (python main.py)")
    print("2. 替换脚本中的 'YOUR_TOKEN_HERE' 为实际的认证token")
    print("3. 运行脚本: python test_new_insight_api.py")
    print("4. 检查后端日志以了解metadata提取过程")
