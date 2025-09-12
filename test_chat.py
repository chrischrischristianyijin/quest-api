#!/usr/bin/env python3
"""
AI聊天功能测试脚本
"""

import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

async def test_chat_health():
    """测试聊天服务健康检查"""
    print("🔍 测试聊天服务健康检查...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8080/api/v1/chat/health")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"健康检查失败: {e}")
            return False

async def test_chat_non_stream():
    """测试非流式聊天"""
    print("\n💬 测试非流式聊天...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            data = {
                "message": "什么是人工智能？请简要介绍一下。"
            }
            
            response = await client.post(
                "http://localhost:8080/api/v1/chat",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"状态码: {response.status_code}")
            result = response.json()
            print(f"成功: {result.get('success')}")
            print(f"回答: {result.get('data', {}).get('response', '')[:200]}...")
            print(f"引用来源数量: {len(result.get('data', {}).get('sources', []))}")
            print(f"延迟: {result.get('data', {}).get('latency_ms')}ms")
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"非流式聊天测试失败: {e}")
            return False

async def test_chat_stream():
    """测试流式聊天"""
    print("\n🌊 测试流式聊天...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            data = {
                "message": "请解释一下机器学习的基本概念"
            }
            
            async with client.stream(
                "POST",
                "http://localhost:8080/api/v1/chat",
                json=data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                print(f"状态码: {response.status_code}")
                print("流式响应:")
                
                full_response = ""
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if data.get('type') == 'content':
                                content = data.get('content', '')
                                print(content, end='', flush=True)
                                full_response += content
                            elif data.get('type') == 'done':
                                print(f"\n\n✅ 流式响应完成")
                                print(f"延迟: {data.get('latency_ms')}ms")
                                print(f"引用来源: {len(data.get('sources', []))}个")
                                break
                        except json.JSONDecodeError:
                            continue
                
                return len(full_response) > 0
                
        except Exception as e:
            print(f"流式聊天测试失败: {e}")
            return False

async def test_rate_limit():
    """测试限流功能"""
    print("\n🚦 测试限流功能...")
    
    async with httpx.AsyncClient() as client:
        try:
            # 快速发送多个请求
            tasks = []
            for i in range(5):
                data = {
                    "message": f"测试请求 {i+1}"
                }
                task = client.post(
                    "http://localhost:8080/api/v1/chat",
                    json=data,
                    headers={"Content-Type": "application/json"}
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = 0
            rate_limit_count = 0
            
            for response in responses:
                if isinstance(response, Exception):
                    print(f"请求异常: {response}")
                elif response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    rate_limit_count += 1
                    print("✅ 限流功能正常工作")
            
            print(f"成功请求: {success_count}")
            print(f"限流请求: {rate_limit_count}")
            
            return True
            
        except Exception as e:
            print(f"限流测试失败: {e}")
            return False

async def main():
    """主测试函数"""
    print("🚀 开始AI聊天功能测试\n")
    
    # 检查环境变量
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
        print("请在.env文件中配置这些变量")
        return
    
    print("✅ 环境变量检查通过")
    
    # 运行测试
    tests = [
        ("健康检查", test_chat_health),
        ("非流式聊天", test_chat_non_stream),
        ("流式聊天", test_chat_stream),
        ("限流功能", test_rate_limit)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    print("\n📊 测试结果汇总:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！AI聊天功能运行正常")
    else:
        print("⚠️ 部分测试失败，请检查配置和日志")

if __name__ == "__main__":
    asyncio.run(main())
