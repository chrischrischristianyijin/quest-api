#!/usr/bin/env python3
"""
测试通过标签ID关联标签的API功能
"""

import requests
import json
import sys

# API配置
BASE_URL = "http://localhost:8000"
INSIGHTS_ENDPOINT = f"{BASE_URL}/api/v1/insights"
USER_TAGS_ENDPOINT = f"{BASE_URL}/api/v1/user-tags"

def test_get_user_tags():
    """测试获取用户标签列表"""
    print("🧪 测试获取用户标签列表")
    print(f"📡 请求地址: {USER_TAGS_ENDPOINT}")
    
    try:
        response = requests.get(
            USER_TAGS_ENDPOINT,
            headers={
                "Authorization": "Bearer YOUR_TOKEN_HERE"  # 需要替换为实际的token
            },
            timeout=10
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功获取标签列表: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 提取标签ID用于后续测试
            if result.get("success") and result.get("data"):
                tags = result.get("data", [])
                tag_ids = [tag.get("id") for tag in tags if tag.get("id")]
                print(f"\n🔍 可用标签ID: {tag_ids}")
                return tag_ids
            else:
                print("❌ 未获取到标签数据")
                return []
        else:
            print(f"❌ 获取标签失败: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
            except:
                print(f"错误内容: {response.text}")
            return []
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
        return []
    except Exception as e:
        print(f"❌ 其他异常: {e}")
        return []

def test_create_insight_with_tag_ids(tag_ids):
    """测试使用标签ID创建见解"""
    if not tag_ids:
        print("❌ 没有可用的标签ID，跳过创建见解测试")
        return
    
    # 使用前3个标签ID（如果可用）
    test_tag_ids = tag_ids[:3]
    
    test_data = {
        "url": "https://www.example.com/test-article",
        "thought": "这是一个测试见解，用于验证标签ID关联功能",
        "tag_ids": test_tag_ids
    }
    
    print(f"\n🧪 测试使用标签ID创建见解")
    print(f"📡 请求地址: {INSIGHTS_ENDPOINT}")
    print(f"📋 请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(
            INSIGHTS_ENDPOINT,
            json=test_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer YOUR_TOKEN_HERE"  # 需要替换为实际的token
            },
            timeout=30
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功创建见解: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
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
                        print(f"    * {tag.get('name')} (ID: {tag.get('id')}, 颜色: {tag.get('color')})")
                        
                    # 验证标签ID是否匹配
                    returned_tag_ids = [tag.get('id') for tag in data.get('tags', [])]
                    if set(returned_tag_ids) == set(test_tag_ids):
                        print("✅ 标签ID关联验证成功")
                    else:
                        print("❌ 标签ID关联验证失败")
                        print(f"  期望: {test_tag_ids}")
                        print(f"  实际: {returned_tag_ids}")
            else:
                print(f"❌ API返回失败: {result.get('message')}")
        else:
            print(f"❌ 创建见解失败: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
            except:
                print(f"错误内容: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
    except Exception as e:
        print(f"❌ 其他异常: {e}")

def test_invalid_tag_ids():
    """测试使用无效的标签ID"""
    print(f"\n🧪 测试使用无效的标签ID")
    
    test_data = {
        "url": "https://www.example.com/test-invalid",
        "thought": "测试无效标签ID的错误处理",
        "tag_ids": [
            "invalid-uuid-format",
            "550e8400-e29b-41d4-a716-446655440999"  # 不存在的UUID
        ]
    }
    
    print(f"📋 请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(
            INSIGHTS_ENDPOINT,
            json=test_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer YOUR_TOKEN_HERE"  # 需要替换为实际的token
            },
            timeout=30
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 422:
            print("✅ 正确返回验证错误（422状态码）")
            try:
                error_detail = response.json()
                print(f"验证错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
            except:
                print(f"错误内容: {response.text}")
        elif response.status_code == 400:
            print("✅ 正确返回业务逻辑错误（400状态码）")
            try:
                error_detail = response.json()
                print(f"业务错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
            except:
                print(f"错误内容: {response.text}")
        else:
            print(f"❌ 意外的响应状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
    except Exception as e:
        print(f"❌ 其他异常: {e}")

if __name__ == "__main__":
    print("🚀 开始测试通过标签ID关联标签的API功能")
    print("=" * 60)
    
    # 步骤1：获取用户标签列表
    tag_ids = test_get_user_tags()
    
    # 步骤2：使用有效标签ID创建见解
    test_create_insight_with_tag_ids(tag_ids)
    
    # 步骤3：测试无效标签ID的错误处理
    test_invalid_tag_ids()
    
    print("\n" + "=" * 60)
    print("🏁 测试完成")
    
    print("\n📝 使用说明:")
    print("1. 确保后端服务正在运行 (python main.py)")
    print("2. 替换脚本中的 'YOUR_TOKEN_HERE' 为实际的认证token")
    print("3. 确保用户已有一些标签")
    print("4. 运行脚本: python test_tag_ids_api.py")
    print("5. 检查后端日志以了解标签ID验证过程")
    
    print("\n🔍 测试要点:")
    print("- 验证通过标签ID直接关联标签")
    print("- 验证标签ID权限检查（只能使用自己的标签）")
    print("- 验证无效标签ID的错误处理")
    print("- 验证metadata自动提取功能")
