#!/usr/bin/env python3
"""
OpenAI API 配置测试脚本
用于验证 OpenAI API 密钥和配置是否正确
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

async def test_openai_config():
    """测试 OpenAI API 配置"""
    print("🔍 开始测试 OpenAI API 配置...")
    print("=" * 50)
    
    # 1. 检查环境变量
    print("1️⃣ 检查环境变量:")
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    summary_enabled = os.getenv('SUMMARY_ENABLED', 'false')
    summary_provider = os.getenv('SUMMARY_PROVIDER', 'openai')
    summary_model = os.getenv('SUMMARY_MODEL', 'gpt-3.5-turbo')
    
    print(f"   OPENAI_API_KEY: {'✅ 已设置' if api_key else '❌ 未设置'}")
    print(f"   OPENAI_BASE_URL: {base_url}")
    print(f"   SUMMARY_ENABLED: {summary_enabled}")
    print(f"   SUMMARY_PROVIDER: {summary_provider}")
    print(f"   SUMMARY_MODEL: {summary_model}")
    
    if not api_key:
        print("\n❌ 错误: OPENAI_API_KEY 未设置")
        print("请按照以下步骤配置:")
        print("1. 访问 https://platform.openai.com/api-keys")
        print("2. 创建新的 API 密钥")
        print("3. 在 .env 文件中设置 OPENAI_API_KEY=sk-your-key")
        return False
    
    # 2. 测试 API 连接
    print("\n2️⃣ 测试 API 连接:")
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    
    # 简单的测试请求
    payload = {
        'model': summary_model,
        'messages': [
            {'role': 'user', 'content': 'Hello, this is a test message.'}
        ],
        'max_tokens': 50
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"   正在连接到: {base_url}")
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                print("   ✅ API 连接成功")
                data = response.json()
                if 'choices' in data and data['choices']:
                    content = data['choices'][0]['message']['content']
                    print(f"   📝 测试响应: {content}")
                return True
            else:
                print(f"   ❌ API 连接失败: HTTP {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
                
    except httpx.ConnectError as e:
        print(f"   ❌ 网络连接错误: {e}")
        return False
    except httpx.TimeoutException as e:
        print(f"   ❌ 请求超时: {e}")
        return False
    except Exception as e:
        print(f"   ❌ 未知错误: {e}")
        return False

async def test_summary_function():
    """测试摘要功能"""
    print("\n3️⃣ 测试摘要功能:")
    
    # 导入摘要函数
    try:
        from app.utils.summarize import generate_summary
        
        test_text = """
        人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，
        它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
        该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
        人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大，
        可以设想，未来人工智能带来的科技产品，将会是人类智慧的"容器"。
        """
        
        print("   正在生成摘要...")
        summary = await generate_summary(test_text)
        
        if summary:
            print("   ✅ 摘要生成成功")
            print(f"   📝 摘要内容: {summary}")
            return True
        else:
            print("   ❌ 摘要生成失败")
            return False
            
    except Exception as e:
        print(f"   ❌ 摘要功能测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 OpenAI API 配置测试工具")
    print("=" * 50)
    
    # 运行测试
    async def run_tests():
        config_ok = await test_openai_config()
        if config_ok:
            await test_summary_function()
        
        print("\n" + "=" * 50)
        if config_ok:
            print("🎉 所有测试通过！OpenAI API 配置正确。")
        else:
            print("❌ 测试失败，请检查配置。")
            print("\n📖 详细配置指南请参考: OPENAI_API_SETUP_GUIDE.md")
    
    # 运行异步测试
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()
