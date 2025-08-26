#!/usr/bin/env python3
"""
快速修复认证问题的脚本
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 加载环境变量
load_dotenv()

def quick_fix_auth():
    """快速修复认证问题"""
    try:
        # 获取Supabase配置
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_service_key:
            print("❌ 缺少Supabase配置")
            print("请检查环境变量：SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")
            return
        
        # 创建Supabase客户端
        supabase: Client = create_client(supabase_url, supabase_service_key)
        
        print("🔧 快速修复认证问题...")
        
        # 1. 检查当前Auth用户数量
        print("\n📋 检查当前Auth用户...")
        try:
            auth_users_response = supabase.auth.admin.list_users()
            if hasattr(auth_users_response, 'data') and auth_users_response.data:
                auth_user_count = len(auth_users_response.data)
                print(f"✅ 当前有 {auth_user_count} 个Auth用户")
                
                # 显示用户邮箱
                for i, user in enumerate(auth_users_response.data[:3]):  # 只显示前3个
                    email = user.get('email', 'N/A')
                    user_id = user.get('id', 'N/A')
                    print(f"  {i+1}. {email} (ID: {user_id[:8]}...)")
                
                if auth_user_count > 3:
                    print(f"  ... 还有 {auth_user_count - 3} 个用户")
            else:
                print("⚠️ 没有找到Auth用户")
        except Exception as e:
            print(f"❌ 检查Auth用户失败: {e}")
            return
        
        # 2. 检查profiles表
        print("\n📋 检查profiles表...")
        try:
            profiles_response = supabase.table('profiles').select('id, nickname').execute()
            if hasattr(profiles_response, 'data') and profiles_response.data:
                profile_count = len(profiles_response.data)
                print(f"✅ profiles表有 {profile_count} 条记录")
                
                # 显示前几个profile
                for i, profile in enumerate(profiles_response.data[:3]):
                    profile_id = profile.get('id', 'N/A')
                    nickname = profile.get('nickname', 'N/A')
                    print(f"  {i+1}. {nickname} (ID: {profile_id[:8]}...)")
            else:
                print("⚠️ profiles表为空")
        except Exception as e:
            print(f"❌ 检查profiles表失败: {e}")
        
        # 3. 提供修复建议
        print("\n💡 修复建议:")
        print("1. 如果Auth用户数量为0，说明所有用户都被删除了")
        print("2. 如果profiles表有记录但Auth用户为0，说明数据不一致")
        print("3. 建议清理所有孤立数据，然后重新开始")
        
        # 4. 询问是否要清理数据
        print("\n🔧 是否要清理所有数据重新开始？")
        print("⚠️  这将删除所有用户数据，包括:")
        print("   - profiles表中的所有记录")
        print("   - user_tags表中的所有记录")
        print("   - insights表中的所有记录")
        print("   - insight_tags表中的所有记录")
        
        response = input("\n是否继续清理？(y/N): ")
        if response.lower() == 'y':
            print("\n🧹 开始清理数据...")
            
            # 清理所有表
            tables_to_clean = ['insight_tags', 'insights', 'user_tags', 'profiles']
            
            for table in tables_to_clean:
                try:
                    print(f"清理 {table} 表...")
                    supabase.table(table).delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                    print(f"✅ {table} 表清理完成")
                except Exception as e:
                    print(f"⚠️ 清理 {table} 表时出错: {e}")
            
            print("\n🎉 数据清理完成！")
            print("现在可以重新注册用户了")
        else:
            print("操作已取消")
        
    except Exception as e:
        print(f"❌ 修复过程中出错: {e}")

if __name__ == "__main__":
    print("🔧 快速修复认证问题")
    print("=" * 40)
    print("此脚本将帮助你诊断和修复认证问题")
    print("=" * 40)
    
    quick_fix_auth()


