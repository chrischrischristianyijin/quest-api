#!/usr/bin/env python3
"""
生产环境 OpenAI API 配置测试
测试 Render 部署的服务是否已正确配置 OpenAI API
"""

import httpx
import asyncio
import json

async def test_production_openai():
    """测试生产环境的 OpenAI API 配置"""
    print("🔍 测试生产环境 OpenAI API 配置...")
    print("=" * 50)
    
    # 测试 URL
    base_url = "https://quest-api-edz1.onrender.com"
    
    # 1. 首先测试健康检查
    print("1️⃣ 测试服务健康状态:")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("   ✅ 服务正常运行")
                health_data = response.json()
                print(f"   📊 状态: {health_data.get('status')}")
                print(f"   🌍 环境: {health_data.get('environment')}")
            else:
                print(f"   ❌ 服务异常: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ 无法连接到服务: {e}")
        return False
    
    # 2. 测试摘要功能（这会触发 OpenAI API 调用）
    print("\n2️⃣ 测试摘要功能:")
    try:
        test_data = {
            "url": "https://example.com",
            "content": """
            人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，
            它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
            该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
            人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大，
            可以设想，未来人工智能带来的科技产品，将会是人类智慧的"容器"。
            """
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("   正在调用元数据提取接口...")
            response = await client.post(
                f"{base_url}/api/v1/metadata/extract",
                data=test_data
            )
            
            print(f"   响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ 接口调用成功")
                data = response.json()
                if data.get('success'):
                    print("   ✅ 摘要功能正常")
                    summary = data.get('data', {}).get('summary')
                    if summary:
                        print(f"   📝 生成的摘要: {summary}")
                    else:
                        print("   ⚠️ 没有生成摘要（可能是配置问题）")
                    return True
                else:
                    print(f"   ❌ 接口返回错误: {data.get('detail', '未知错误')}")
                    return False
            elif response.status_code == 401:
                print("   ❌ 认证失败 - 可能需要登录")
                return False
            elif response.status_code == 500:
                print("   ❌ 服务器内部错误")
                try:
                    error_data = response.json()
                    print(f"   错误详情: {error_data}")
                except:
                    print(f"   错误响应: {response.text[:200]}")
                return False
            else:
                print(f"   ❌ 意外状态码: {response.status_code}")
                print(f"   响应内容: {response.text[:200]}")
                return False
                
    except httpx.TimeoutException:
        print("   ❌ 请求超时")
        return False
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 生产环境 OpenAI API 测试工具")
    print("=" * 50)
    
    async def run_test():
        success = await test_production_openai()
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 生产环境 OpenAI API 配置正确！")
            print("✅ 摘要功能可以正常工作")
        else:
            print("❌ 生产环境配置有问题")
            print("\n🔧 可能的解决方案:")
            print("1. 检查 Render Dashboard 中的环境变量配置")
            print("2. 确认 OPENAI_API_KEY 已正确设置")
            print("3. 检查 API 密钥是否有效")
            print("4. 查看 Render 部署日志")
    
    asyncio.run(run_test())

if __name__ == "__main__":
    main()
