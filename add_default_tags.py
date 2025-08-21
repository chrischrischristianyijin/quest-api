#!/usr/bin/env python3
"""
为用户添加初始英文标签的脚本
运行此脚本可以为新用户或现有用户添加一些常用的英文标签
"""

import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 加载环境变量
load_dotenv()

# 初始化Supabase客户端
supabase_url = os.getenv('SUPABASE_URL')
supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not supabase_url or not supabase_service_key:
    print("❌ 环境变量未设置")
    exit(1)

supabase: Client = create_client(supabase_url, supabase_service_key)

# 初始标签配置
DEFAULT_TAGS = [
    # 技术相关
    {"name": "Technology", "color": "#3B82F6"},
    {"name": "Programming", "color": "#10B981"},
    {"name": "AI", "color": "#8B5CF6"},
    {"name": "Web Development", "color": "#EF4444"},
    
    # 学习相关
    {"name": "Learning", "color": "#84CC16"},
    {"name": "Tutorial", "color": "#F97316"},
    
    # 内容类型
    {"name": "Article", "color": "#059669"},
    {"name": "Video", "color": "#DC2626"},
    
    # 主题分类
    {"name": "Business", "color": "#1F2937"},
    {"name": "Productivity", "color": "#047857"},
    {"name": "Design", "color": "#BE185D"},
    
    # 工具和资源
    {"name": "Tool", "color": "#7C2D12"},
    {"name": "Resource", "color": "#1E40AF"},
    
    # 项目相关
    {"name": "Project", "color": "#7C3AED"},
    {"name": "Ideas", "color": "#F59E0B"}
]

async def add_default_tags_for_user(user_id: str):
    """为指定用户添加默认标签"""
    try:
        print(f"🔄 为用户 {user_id} 添加默认标签...")
        
        # 检查用户是否已有标签
        existing_tags = supabase.table('user_tags').select('name').eq('user_id', user_id).execute()
        existing_tag_names = [tag['name'] for tag in existing_tags.data] if existing_tags.data else []
        
        # 过滤掉已存在的标签
        new_tags = [tag for tag in DEFAULT_TAGS if tag['name'] not in existing_tag_names]
        
        if not new_tags:
            print(f"✅ 用户 {user_id} 已有所有默认标签")
            return
        
        # 批量插入新标签
        for tag in new_tags:
            tag_data = {
                "user_id": user_id,
                "name": tag["name"],
                "color": tag["color"]
            }
            
            result = supabase.table('user_tags').insert(tag_data).execute()
            if result.data:
                print(f"✅ 添加标签: {tag['name']}")
            else:
                print(f"❌ 添加标签失败: {tag['name']}")
        
        print(f"🎉 为用户 {user_id} 添加了 {len(new_tags)} 个新标签")
        
    except Exception as e:
        print(f"❌ 为用户 {user_id} 添加标签时出错: {e}")

async def add_default_tags_for_all_users():
    """为所有用户添加默认标签"""
    try:
        print("🔄 获取所有用户...")
        
        # 获取所有用户
        users_response = supabase.auth.admin.list_users()
        if not users_response.users:
            print("❌ 没有找到用户")
            return
        
        print(f"📊 找到 {len(users_response.users)} 个用户")
        
        # 为每个用户添加默认标签
        for user in users_response.users:
            await add_default_tags_for_user(user.id)
            print("-" * 50)
        
        print("🎉 所有用户的默认标签添加完成！")
        
    except Exception as e:
        print(f"❌ 获取用户列表时出错: {e}")

async def add_default_tags_for_specific_user(email: str):
    """为指定邮箱的用户添加默认标签"""
    try:
        print(f"🔄 查找用户: {email}")
        
        # 通过邮箱查找用户
        user_response = supabase.auth.admin.list_users()
        target_user = None
        
        for user in user_response.users:
            if user.email == email:
                target_user = user
                break
        
        if not target_user:
            print(f"❌ 未找到用户: {email}")
            return
        
        print(f"✅ 找到用户: {target_user.email} (ID: {target_user.id})")
        await add_default_tags_for_user(target_user.id)
        
    except Exception as e:
        print(f"❌ 查找用户时出错: {e}")

async def main():
    """主函数"""
    print("🚀 Quest API - 默认标签添加脚本")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 为所有用户添加默认标签")
        print("2. 为指定邮箱的用户添加默认标签")
        print("3. 为指定用户ID添加默认标签")
        print("4. 查看默认标签列表")
        print("5. 退出")
        
        choice = input("\n请输入选择 (1-5): ").strip()
        
        if choice == "1":
            await add_default_tags_for_all_users()
        elif choice == "2":
            email = input("请输入用户邮箱: ").strip()
            if email:
                await add_default_tags_for_specific_user(email)
            else:
                print("❌ 邮箱不能为空")
        elif choice == "3":
            user_id = input("请输入用户ID: ").strip()
            if user_id:
                await add_default_tags_for_user(user_id)
            else:
                print("❌ 用户ID不能为空")
        elif choice == "4":
            print("\n📋 默认标签列表:")
            for i, tag in enumerate(DEFAULT_TAGS, 1):
                print(f"{i:2d}. {tag['name']} ({tag['color']}) - {tag['description']}")
        elif choice == "5":
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    asyncio.run(main())
