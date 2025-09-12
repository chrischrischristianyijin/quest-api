#!/usr/bin/env python3
"""
测试GPT-5 mini关键词提取功能
"""
import asyncio
import os
import sys
import httpx
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_gpt5_mini():
    """测试GPT-5 mini API调用"""
    print("🔍 测试GPT-5 mini关键词提取")
    print("=" * 50)
    
    # 检查环境变量
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
        return
    
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    
    # 测试用例
    test_query = "如何提高Python代码的性能？"
    
    keyword_prompt = (
        "Extract 2–5 abstracted keywords from the following user question for vector retrieval.\n"
        "Go beyond literal words if needed: include related concepts, entities, or topics that capture the intent behind the question.\n"
        "Keep them concise, specific, and semantically meaningful.\n"
        "Do not include filler words (e.g., \"how\", \"problem\", \"situation\").\n"
        "Keep the same language as the original question (Chinese → Chinese keywords, English → English keywords).\n"
        "Output only the keywords, separated by commas. No explanations, no numbering, no line breaks.\n\n"
        f"User question: {test_query}\n\n"
        "Keywords:"
    )
    
    # GPT-5 mini 参数
    payload = {
        'model': 'gpt-5-mini',
        'messages': [
            {"role": "user", "content": keyword_prompt}
        ],
        'temperature': 0.1,
        'max_completion_tokens': 100,
        'verbosity': 'low',
        'reasoning_effort': 'minimal'
    }
    
    print(f"📝 测试问题: {test_query}")
    print("-" * 30)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                keywords = data['choices'][0]['message']['content'].strip()
                print(f"✅ 提取的关键词: {keywords}")
                
                # 显示使用情况
                if 'usage' in data:
                    usage = data['usage']
                    print(f"✅ Token使用: 输入={usage.get('prompt_tokens', 0)}, 输出={usage.get('completion_tokens', 0)}")
                
            else:
                print(f"❌ API调用失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"错误详情: {error_detail}")
            except:
                print(f"响应状态: {e.response.status_code}")
    
    print("\n🎉 测试完成!")

if __name__ == "__main__":
    asyncio.run(test_gpt5_mini())
