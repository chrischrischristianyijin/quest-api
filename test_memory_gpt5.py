#!/usr/bin/env python3
"""
测试GPT-5 mini的记忆功能
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.memory_service import MemoryService
from uuid import uuid4

async def test_memory_gpt5():
    """测试GPT-5 mini的记忆功能"""
    print("🧠 测试GPT-5 mini的记忆功能")
    print("=" * 50)
    
    # 检查环境变量
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
        return
    
    memory_service = MemoryService()
    print(f"📋 使用的模型: {memory_service.chat_model}")
    
    # 测试会话ID
    test_session_id = uuid4()
    
    # 模拟对话历史
    conversation_history = [
        {"role": "user", "content": "我喜欢在早上工作，因为那时候头脑最清醒"},
        {"role": "assistant", "content": "我记住了！你更喜欢在早上工作，因为那时候效率最高。"},
        {"role": "user", "content": "我最近在学习Python，特别是数据科学方面的内容"},
        {"role": "assistant", "content": "很好！Python在数据科学领域确实很强大。你主要关注哪些库？"}
    ]
    
    print(f"📝 测试对话历史:")
    for msg in conversation_history:
        print(f"  {msg['role']}: {msg['content']}")
    print("-" * 30)
    
    try:
        # 测试记忆提取
        print("1️⃣ 测试记忆提取...")
        memories = await memory_service.extract_memories_from_conversation(
            conversation_history, test_session_id
        )
        
        print(f"✅ 提取了 {len(memories)} 个记忆:")
        for i, memory in enumerate(memories, 1):
            print(f"  {i}. [{memory.memory_type.value}] {memory.content}")
            print(f"     重要性: {memory.importance_score}")
        
        # 测试记忆创建
        if memories:
            print("\n2️⃣ 测试记忆创建...")
            created_memories = await memory_service.create_memories(memories)
            print(f"✅ 成功创建 {len(created_memories)} 个记忆")
        
        # 测试记忆检索
        print("\n3️⃣ 测试记忆检索...")
        query = "工作时间和学习内容"
        relevant_memories = await memory_service.get_relevant_memories(
            test_session_id, query, limit=3
        )
        
        print(f"✅ 找到 {len(relevant_memories)} 个相关记忆:")
        for i, memory in enumerate(relevant_memories, 1):
            print(f"  {i}. {memory.content}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 测试完成!")

if __name__ == "__main__":
    asyncio.run(test_memory_gpt5())
