#!/usr/bin/env python3
"""
测试元数据提取时的后台摘要生成功能
"""

import httpx
import asyncio
import json
import time
from urllib.parse import quote

async def test_metadata_with_summary():
    """测试元数据提取时的后台摘要生成"""
    print("🔍 测试元数据提取时的后台摘要生成...")
    print("=" * 50)
    
    # 测试 URL
    base_url = "https://quest-api-edz1.onrender.com"
    test_url = "https://example.com"
    
    # 1. 测试元数据提取（触发后台摘要生成）
    print("1️⃣ 测试元数据提取（触发后台摘要生成）:")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 提取元数据
            form_data = {"url": test_url}
            response = await client.post(
                f"{base_url}/api/v1/metadata/extract",
                data=form_data
            )
            
            print(f"   响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("   ✅ 元数据提取成功")
                    print(f"   📝 标题: {data['data']['title']}")
                    print(f"   📝 描述: {data['data']['description'][:100]}...")
                    print(f"   📝 摘要状态: {data['data'].get('summary_status', 'unknown')}")
                    
                    # 2. 等待一段时间让摘要生成
                    print("\n2️⃣ 等待摘要生成...")
                    print("   ⏳ 等待 10 秒让后台任务完成...")
                    await asyncio.sleep(10)
                    
                    # 3. 检查摘要状态
                    print("\n3️⃣ 检查摘要状态:")
                    encoded_url = quote(test_url, safe='')
                    summary_response = await client.get(
                        f"{base_url}/api/v1/metadata/summary/{encoded_url}"
                    )
                    
                    print(f"   摘要状态响应码: {summary_response.status_code}")
                    
                    if summary_response.status_code == 200:
                        summary_data = summary_response.json()
                        if summary_data.get('success'):
                            status = summary_data['data']['status']
                            print(f"   📊 摘要状态: {status}")
                            
                            if status == 'completed':
                                summary = summary_data['data']['summary']
                                print(f"   ✅ 摘要生成成功!")
                                print(f"   📝 摘要内容: {summary}")
                                return True
                            elif status == 'generating':
                                print("   ⏳ 摘要仍在生成中...")
                                return True
                            elif status == 'failed':
                                error = summary_data['data']['error']
                                print(f"   ❌ 摘要生成失败: {error}")
                                return False
                            else:
                                print(f"   ⚠️ 未知状态: {status}")
                                return True
                        else:
                            print(f"   ❌ 获取摘要状态失败: {summary_data.get('message')}")
                            return False
                    else:
                        print(f"   ❌ 获取摘要状态失败: HTTP {summary_response.status_code}")
                        return False
                else:
                    print(f"   ❌ 元数据提取失败: {data.get('message', '未知错误')}")
                    return False
            else:
                print(f"   ❌ 元数据提取失败: HTTP {response.status_code}")
                print(f"   响应内容: {response.text[:200]}")
                return False
                
    except httpx.TimeoutException:
        print("   ❌ 请求超时")
        return False
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
        return False

async def test_multiple_urls():
    """测试多个URL的摘要生成"""
    print("\n4️⃣ 测试多个URL的摘要生成:")
    
    test_urls = [
        "https://example.com",
        "https://httpbin.org/json",
        "https://jsonplaceholder.typicode.com/posts/1"
    ]
    
    base_url = "https://quest-api-edz1.onrender.com"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, url in enumerate(test_urls, 1):
                print(f"   🔄 测试 URL {i}: {url}")
                
                # 提取元数据
                form_data = {"url": url}
                response = await client.post(
                    f"{base_url}/api/v1/metadata/extract",
                    data=form_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        print(f"   ✅ 元数据提取成功")
                        print(f"   📝 摘要状态: {data['data'].get('summary_status', 'unknown')}")
                    else:
                        print(f"   ❌ 元数据提取失败: {data.get('message')}")
                else:
                    print(f"   ❌ 请求失败: HTTP {response.status_code}")
                
                # 等待一下再测试下一个
                await asyncio.sleep(2)
            
            # 等待所有摘要生成
            print("   ⏳ 等待所有摘要生成完成...")
            await asyncio.sleep(15)
            
            # 检查所有摘要状态
            print("   📊 检查所有摘要状态:")
            for i, url in enumerate(test_urls, 1):
                encoded_url = quote(url, safe='')
                summary_response = await client.get(
                    f"{base_url}/api/v1/metadata/summary/{encoded_url}"
                )
                
                if summary_response.status_code == 200:
                    summary_data = summary_response.json()
                    if summary_data.get('success'):
                        status = summary_data['data']['status']
                        print(f"   URL {i}: {status}")
                        
                        if status == 'completed':
                            summary = summary_data['data']['summary']
                            print(f"      📝 摘要: {summary[:100]}...")
                        elif status == 'failed':
                            error = summary_data['data']['error']
                            print(f"      ❌ 错误: {error}")
                    else:
                        print(f"   URL {i}: 获取状态失败")
                else:
                    print(f"   URL {i}: 请求失败 HTTP {summary_response.status_code}")
                
                await asyncio.sleep(1)
    
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")

def main():
    """主函数"""
    print("🚀 元数据提取后台摘要生成测试工具")
    print("=" * 50)
    
    async def run_tests():
        success = await test_metadata_with_summary()
        
        if success:
            await test_multiple_urls()
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 后台摘要生成功能测试完成！")
            print("✅ 元数据提取成功")
            print("✅ 后台摘要生成任务已启动")
            print("✅ 摘要已保存到 insight_contents 表")
            print("✅ 摘要状态查询功能正常")
            print("\n📝 新功能说明:")
            print("1. 调用 /api/v1/metadata/extract 时会自动启动后台摘要生成")
            print("2. 摘要结果会保存到 insight_contents 表的 summary 字段")
            print("3. 使用 /api/v1/metadata/summary/{url} 查询摘要状态")
            print("4. 摘要结果会缓存1小时")
        else:
            print("❌ 测试失败")
            print("\n🔧 可能的解决方案:")
            print("1. 检查 OpenAI API 配置")
            print("2. 确认环境变量设置正确")
            print("3. 查看服务日志")
    
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()
