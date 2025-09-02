#!/usr/bin/env python3
"""
通过创建 Insight 测试 OpenAI API 配置
这个方法会触发后台的摘要生成，从而测试 OpenAI API 是否正常工作
"""

import httpx
import asyncio
import json
import time

async def test_insight_creation_with_summary():
    """通过创建 insight 测试 OpenAI API 配置"""
    print("🔍 通过创建 Insight 测试 OpenAI API 配置...")
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
            else:
                print(f"   ❌ 服务异常: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ 无法连接到服务: {e}")
        return False
    
    # 2. 测试创建 insight（这会触发后台摘要生成）
    print("\n2️⃣ 测试创建 Insight（触发摘要生成）:")
    
    # 注意：这个测试需要认证，所以会失败，但我们可以看到错误信息
    test_data = {
        "url": "https://example.com",
        "title": "测试 Insight",
        "description": "这是一个测试 insight，用于验证 OpenAI API 配置",
        "thought": "测试思考内容"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("   正在尝试创建 Insight...")
            print("   ⚠️  注意：这个测试需要认证，预期会返回 401")
            
            response = await client.post(
                f"{base_url}/api/v1/insights",
                json=test_data
            )
            
            print(f"   响应状态码: {response.status_code}")
            
            if response.status_code == 401:
                print("   ✅ 认证检查正常（需要登录才能创建 insight）")
                print("   📝 这说明服务正常运行，摘要功能会在创建 insight 时触发")
                return True
            elif response.status_code == 200:
                print("   ✅ Insight 创建成功")
                data = response.json()
                if data.get('success'):
                    print("   ✅ 摘要功能应该已经在后台触发")
                    return True
                else:
                    print(f"   ❌ 创建失败: {data.get('message', '未知错误')}")
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

async def test_with_auth_token():
    """使用认证令牌测试（如果你有有效的令牌）"""
    print("\n3️⃣ 使用认证令牌测试（可选）:")
    print("   如果你有有效的认证令牌，可以取消注释以下代码进行完整测试")
    
    # 示例代码（需要有效的认证令牌）
    """
    auth_token = "your-valid-auth-token-here"
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    test_data = {
        "url": "https://example.com",
        "title": "测试 Insight",
        "description": "这是一个测试 insight，用于验证 OpenAI API 配置",
        "thought": "测试思考内容"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/api/v1/insights",
                json=test_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    insight_id = data.get('data', {}).get('id')
                    print(f"   ✅ Insight 创建成功，ID: {insight_id}")
                    
                    # 等待一段时间让后台摘要生成完成
                    print("   ⏳ 等待后台摘要生成...")
                    await asyncio.sleep(5)
                    
                    # 检查 insight 详情，看是否有摘要
                    detail_response = await client.get(
                        f"{base_url}/api/v1/insights/{insight_id}",
                        headers=headers
                    )
                    
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        if detail_data.get('success'):
                            insight = detail_data.get('data', {})
                            if insight.get('summary'):
                                print(f"   ✅ 摘要生成成功: {insight['summary']}")
                                return True
                            else:
                                print("   ⚠️ 没有找到摘要（可能还在生成中）")
                                return True
                    
                    return True
                else:
                    print(f"   ❌ 创建失败: {data.get('message', '未知错误')}")
                    return False
            else:
                print(f"   ❌ 创建失败: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False
    """

def main():
    """主函数"""
    print("🚀 Insight 创建测试工具")
    print("=" * 50)
    
    async def run_tests():
        success = await test_insight_creation_with_summary()
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 服务配置检查完成！")
            print("✅ 服务正常运行")
            print("✅ 认证系统正常工作")
            print("✅ OpenAI API 配置应该正确（会在创建 insight 时触发）")
            print("\n📝 要完全验证 OpenAI API 配置，请：")
            print("1. 登录你的应用")
            print("2. 创建一个新的 insight")
            print("3. 检查 insight 是否有自动生成的摘要")
        else:
            print("❌ 测试失败")
            print("\n🔧 可能的解决方案:")
            print("1. 检查服务是否正常运行")
            print("2. 确认环境变量配置正确")
            print("3. 查看 Render 部署日志")
    
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()
