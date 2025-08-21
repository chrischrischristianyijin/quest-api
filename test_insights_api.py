#!/usr/bin/env python3
"""
Quest API Insights 测试脚本
演示见解、评论和标签API的使用
"""

import requests
import json

# API基础URL
BASE_URL = "http://localhost:3001/api/v1"

def test_insights_api():
    """测试见解相关API"""
    print("🔍 测试见解相关API...")
    
    # 1. 获取见解列表
    print("\n1️⃣ 获取见解列表")
    response = requests.get(f"{BASE_URL}/insights")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误: {response.text}")
    
    # 2. 获取见解列表（带分页和筛选）
    print("\n2️⃣ 获取见解列表（分页+筛选）")
    response = requests.get(f"{BASE_URL}/insights?page=1&limit=5&search=技术")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误: {response.text}")

def test_user_tags_api():
    """测试用户标签相关API"""
    print("\n🔍 测试用户标签相关API...")
    
    # 1. 获取标签列表
    print("\n1️⃣ 获取用户标签列表")
    response = requests.get(f"{BASE_URL}/user-tags")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误: {response.text}")
    
    # 2. 获取标签统计
    print("\n2️⃣ 获取标签统计")
    response = requests.get(f"{BASE_URL}/user-tags/stats/overview")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误: {response.text}")
    
    # 3. 搜索标签
    print("\n3️⃣ 搜索标签")
    response = requests.get(f"{BASE_URL}/user-tags/search?query=技术")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误: {response.text}")

def test_insight_detail():
    """测试见解详情API"""
    print("\n🔍 测试见解详情API...")
    
    # 获取见解详情（需要有效的insight_id）
    insight_id = "example-insight-id"  # 这里需要替换为实际的ID
    print(f"\n1️⃣ 获取见解详情 (ID: {insight_id})")
    response = requests.get(f"{BASE_URL}/insights/{insight_id}")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误: {response.text}")

def test_authenticated_apis():
    """测试需要认证的API（需要先登录获取token）"""
    print("\n🔍 测试需要认证的API...")
    
    # 这里需要先登录获取access_token
    print("⚠️  需要先登录获取access_token才能测试以下API:")
    print("   - 创建见解")
    print("   - 更新见解")
    print("   - 删除见解")
    print("   - 创建评论")
    print("   - 创建标签")
    print("   - 更新标签")
    print("   - 删除标签")

def show_api_examples():
    """显示API使用示例"""
    print("\n📚 API使用示例")
    print("=" * 50)
    
    print("\n🔹 创建见解示例:")
    print("POST /api/v1/insights")
    print("Headers: Authorization: Bearer <access_token>")
    print("Body:")
    print(json.dumps({
        "title": "我的第一个见解",
        "description": "这是一个关于技术的见解",
        "image_url": "https://example.com/image.jpg",
        "tags": ["技术", "学习", "编程"]
    }, indent=2, ensure_ascii=False))
    
    print("\n🔹 创建评论示例:")
    print("POST /api/v1/insights/{insight_id}/comments")
    print("Headers: Authorization: Bearer <access_token>")
    print("Body:")
    print(json.dumps({
        "content": "这是一个很有用的见解！"
    }, indent=2, ensure_ascii=False))
    
    print("\n🔹 创建标签示例:")
    print("POST /api/v1/user-tags")
    print("Headers: Authorization: Bearer <access_token>")
    print("Body:")
    print(json.dumps({
        "name": "技术",
        "color": "#3B82F6",
        "description": "技术相关的标签"
    }, indent=2, ensure_ascii=False))
    
    print("\n🔹 获取见解列表（带筛选）:")
    print("GET /api/v1/insights?page=1&limit=10&tag=技术&search=编程")
    
    print("\n🔹 获取标签统计:")
    print("GET /api/v1/user-tags/stats/overview")
    print("Headers: Authorization: Bearer <access_token>")

def main():
    """主函数"""
    print("🚀 Quest API Insights 测试")
    print("=" * 50)
    
    try:
        # 测试不需要认证的API
        test_insights_api()
        test_user_tags_api()
        test_insight_detail()
        
        # 显示需要认证的API示例
        test_authenticated_apis()
        
        # 显示API使用示例
        show_api_examples()
        
        print("\n✅ 测试完成！")
        print("\n💡 要测试需要认证的API，请先:")
        print("   1. 运行: python3 test_api_examples.py")
        print("   2. 获取access_token")
        print("   3. 使用token测试其他API")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到API服务器，请确保服务器正在运行")
        print("💡 运行命令: python3 main.py")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()
