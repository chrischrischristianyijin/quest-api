#!/usr/bin/env python3
"""
AI聊天功能简单使用示例
"""

import requests
import json

def simple_chat(question, api_url="http://localhost:8080/api/v1/chat"):
    """简单的聊天函数"""
    try:
        # 发送聊天请求
        response = requests.post(
            f"{api_url}",
            json={
                "message": question
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                data = result.get("data", {})
                print(f"🤖 AI回答: {data.get('response', '')}")
                print(f"📚 引用来源: {len(data.get('sources', []))} 个")
                print(f"⏱️ 响应时间: {data.get('latency_ms', 0)}ms")
                return True
            else:
                print(f"❌ 请求失败: {result.get('message', '')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")
    
    return False

def main():
    """主函数"""
    print("🤖 Quest AI聊天示例")
    print("=" * 50)
    
    # 测试问题列表
    questions = [
        "什么是人工智能？",
        "请介绍一下机器学习的基本概念",
        "深度学习有什么应用？",
        "如何学习编程？"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n📝 问题 {i}: {question}")
        print("-" * 30)
        
        success = simple_chat(question)
        
        if not success:
            print("⚠️ 请确保API服务正在运行")
            break
        
        print("✅ 回答完成")
    
    print("\n" + "=" * 50)
    print("🎉 示例完成！")

if __name__ == "__main__":
    main()
