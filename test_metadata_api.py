#!/usr/bin/env python3
"""
Quest API Metadata 测试脚本
演示网页元数据提取和insight创建功能
"""

import requests
import json

# API基础URL
BASE_URL = "http://localhost:3001/api/v1"

def test_metadata_extraction():
    """测试元数据提取功能"""
    print("🔍 测试元数据提取功能...")
    
    # 测试URL
    test_urls = [
        "https://www.python.org/",
        "https://fastapi.tiangolo.com/",
        "https://supabase.com/"
    ]
    
    for url in test_urls:
        print(f"\n📄 提取URL: {url}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/metadata/extract",
                data={"url": url}
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 提取成功:")
                print(f"   标题: {result['data']['title']}")
                print(f"   描述: {result['data']['description'][:100]}...")
                print(f"   图片: {result['data']['image_url']}")
                print(f"   域名: {result['data']['domain']}")
            else:
                print(f"❌ 提取失败: {response.text}")
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")

def test_batch_extraction():
    """测试批量元数据提取"""
    print("\n🔍 测试批量元数据提取...")
    
    urls = """
https://www.python.org/
https://fastapi.tiangolo.com/
https://supabase.com/
    """.strip()
    
    try:
        response = requests.post(
            f"{BASE_URL}/metadata/batch-extract",
            data={"urls": urls}
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 批量提取成功:")
            for item in result['data']:
                status = "✅" if item['success'] else "❌"
                print(f"   {status} {item['url']}")
                if not item['success']:
                    print(f"      错误: {item['error']}")
        else:
            print(f"❌ 批量提取失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_create_insight_from_url():
    """测试从URL创建insight（需要认证）"""
    print("\n🔍 测试从URL创建insight...")
    
    print("⚠️  这个功能需要认证，请先登录获取access_token")
    print("💡 使用示例:")
    print("POST /api/v1/metadata/create-insight")
    print("Headers: Authorization: Bearer <access_token>")
    print("Form Data:")
    print("  - url: https://www.python.org/")
    print("  - title: 自定义标题（可选）")
    print("  - description: 自定义描述（可选）")
    print("  - tags: 标签1,标签2,标签3（可选）")

def test_insight_preview():
    """测试insight预览功能（需要认证）"""
    print("\n🔍 测试insight预览功能...")
    
    print("⚠️  这个功能需要认证，请先登录获取access_token")
    print("💡 使用示例:")
    print("GET /api/v1/metadata/preview/{insight_id}")
    print("Headers: Authorization: Bearer <access_token>")

def show_api_examples():
    """显示API使用示例"""
    print("\n📚 Metadata API 使用示例")
    print("=" * 50)
    
    print("\n🔹 提取单个URL的元数据:")
    print("POST /api/v1/metadata/extract")
    print("Form Data: url=https://www.python.org/")
    
    print("\n🔹 批量提取多个URL的元数据:")
    print("POST /api/v1/metadata/batch-extract")
    print("Form Data: urls=https://url1.com\\nhttps://url2.com")
    
    print("\n🔹 从URL创建insight:")
    print("POST /api/v1/metadata/create-insight")
    print("Headers: Authorization: Bearer <access_token>")
    print("Form Data:")
    print("  - url: https://www.python.org/")
    print("  - title: Python官网")
    print("  - description: Python编程语言官方网站")
    print("  - tags: Python,编程,官网")
    
    print("\n🔹 预览insight内容:")
    print("GET /api/v1/metadata/preview/{insight_id}")
    print("Headers: Authorization: Bearer <access_token>")

def show_frontend_integration():
    """显示前端集成示例"""
    print("\n💻 前端集成示例")
    print("=" * 50)
    
    print("\n🔹 JavaScript Fetch API 示例:")
    print("""
// 提取网页元数据
const extractMetadata = async (url) => {
  const formData = new FormData();
  formData.append('url', url);
  
  const response = await fetch('/api/v1/metadata/extract', {
    method: 'POST',
    body: formData
  });
  
  return response.json();
};

// 从URL创建insight
const createInsightFromUrl = async (url, customData = {}) => {
  const formData = new FormData();
  formData.append('url', url);
  
  if (customData.title) formData.append('title', customData.title);
  if (customData.description) formData.append('description', customData.description);
  if (customData.tags) formData.append('tags', customData.tags.join(','));
  
  const response = await fetch('/api/v1/metadata/create-insight', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    },
    body: formData
  });
  
  return response.json();
};

// 批量提取元数据
const batchExtractMetadata = async (urls) => {
  const formData = new FormData();
  formData.append('urls', urls.join('\\n'));
  
  const response = await fetch('/api/v1/metadata/batch-extract', {
    method: 'POST',
    body: formData
  });
  
  return response.json();
};
    """)

def main():
    """主函数"""
    print("🚀 Quest API Metadata 测试")
    print("=" * 50)
    
    try:
        # 测试不需要认证的API
        test_metadata_extraction()
        test_batch_extraction()
        
        # 显示需要认证的API示例
        test_create_insight_from_url()
        test_insight_preview()
        
        # 显示API使用示例
        show_api_examples()
        
        # 显示前端集成示例
        show_frontend_integration()
        
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

