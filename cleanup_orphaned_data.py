#!/usr/bin/env python3
"""
清理孤立数据的脚本 - 解决手动删除Supabase用户后的数据不一致问题
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 加载环境变量
load_dotenv()

def cleanup_orphaned_data():
    """清理孤立的数据记录"""
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
        
        print("🧹 开始清理孤立数据...")
        
        # 1. 获取所有Supabase Auth用户
        print("\n📋 步骤1: 获取Supabase Auth用户列表...")
        try:
            auth_users_response = supabase.auth.admin.list_users()
            if hasattr(auth_users_response, 'data') and auth_users_response.data:
                auth_user_ids = [user.get('id') for user in auth_users_response.data if user.get('id')]
                print(f"✅ 找到 {len(auth_user_ids)} 个Auth用户")
                print(f"Auth用户ID列表: {auth_user_ids[:5]}...")  # 只显示前5个
            else:
                auth_user_ids = []
                print("⚠️ 没有找到Auth用户")
        except Exception as e:
            print(f"❌ 获取Auth用户失败: {e}")
            auth_user_ids = []
        
        # 2. 检查profiles表中的孤立记录
        print("\n📋 步骤2: 检查profiles表中的孤立记录...")
        try:
            profiles_response = supabase.table('profiles').select('id').execute()
            if hasattr(profiles_response, 'data') and profiles_response.data:
                profile_ids = [profile.get('id') for profile in profiles_response.data if profile.get('id')]
                print(f"✅ 找到 {len(profile_ids)} 个profile记录")
                
                # 找出孤立的profile记录（在profiles表中但不在auth.users中）
                orphaned_profiles = [pid for pid in profile_ids if pid not in auth_user_ids]
                if orphaned_profiles:
                    print(f"⚠️ 发现 {len(orphaned_profiles)} 个孤立的profile记录")
                    print(f"孤立记录ID: {orphaned_profiles[:5]}...")
                    
                    # 询问是否删除
                    response = input(f"\n是否删除这 {len(orphaned_profiles)} 个孤立的profile记录？(y/N): ")
                    if response.lower() == 'y':
                        for orphaned_id in orphaned_profiles:
                            try:
                                supabase.table('profiles').delete().eq('id', orphaned_id).execute()
                                print(f"✅ 已删除孤立profile: {orphaned_id}")
                            except Exception as e:
                                print(f"❌ 删除profile {orphaned_id} 失败: {e}")
                else:
                    print("✅ 没有发现孤立的profile记录")
            else:
                print("⚠️ profiles表为空或不存在")
        except Exception as e:
            print(f"❌ 检查profiles表失败: {e}")
        
        # 3. 检查user_tags表中的孤立记录
        print("\n📋 步骤3: 检查user_tags表中的孤立记录...")
        try:
            user_tags_response = supabase.table('user_tags').select('user_id').execute()
            if hasattr(user_tags_response, 'data') and user_tags_response.data:
                user_tag_user_ids = [tag.get('user_id') for tag in user_tags_response.data if tag.get('user_id')]
                print(f"✅ 找到 {len(user_tag_user_ids)} 个user_tag记录")
                
                # 找出孤立的user_tag记录
                orphaned_user_tags = [uid for uid in user_tag_user_ids if uid not in auth_user_ids]
                if orphaned_user_tags:
                    print(f"⚠️ 发现 {len(orphaned_user_tags)} 个孤立的user_tag记录")
                    print(f"孤立记录用户ID: {orphaned_user_tags[:5]}...")
                    
                    # 询问是否删除
                    response = input(f"\n是否删除这 {len(orphaned_user_tags)} 个孤立的user_tag记录？(y/N): ")
                    if response.lower() == 'y':
                        for orphaned_uid in orphaned_user_tags:
                            try:
                                supabase.table('user_tags').delete().eq('user_id', orphaned_uid).execute()
                                print(f"✅ 已删除孤立user_tag: {orphaned_uid}")
                            except Exception as e:
                                print(f"❌ 删除user_tag {orphaned_uid} 失败: {e}")
                else:
                    print("✅ 没有发现孤立的user_tag记录")
            else:
                print("⚠️ user_tags表为空或不存在")
        except Exception as e:
            print(f"❌ 检查user_tags表失败: {e}")
        
        # 4. 检查insights表中的孤立记录
        print("\n📋 步骤4: 检查insights表中的孤立记录...")
        try:
            insights_response = supabase.table('insights').select('user_id').execute()
            if hasattr(insights_response, 'data') and insights_response.data:
                insight_user_ids = [insight.get('user_id') for insight in insights_response.data if insight.get('user_id')]
                print(f"✅ 找到 {len(insight_user_ids)} 个insight记录")
                
                # 找出孤立的insight记录
                orphaned_insights = [uid for uid in insight_user_ids if uid not in auth_user_ids]
                if orphaned_insights:
                    print(f"⚠️ 发现 {len(orphaned_insights)} 个孤立的insight记录")
                    print(f"孤立记录用户ID: {orphaned_insights[:5]}...")
                    
                    # 询问是否删除
                    response = input(f"\n是否删除这 {len(orphaned_insights)} 个孤立的insight记录？(y/N): ")
                    if response.lower() == 'y':
                        for orphaned_uid in orphaned_insights:
                            try:
                                supabase.table('insights').delete().eq('user_id', orphaned_uid).execute()
                                print(f"✅ 已删除孤立insight: {orphaned_uid}")
                            except Exception as e:
                                print(f"❌ 删除insight {orphaned_uid} 失败: {e}")
                else:
                    print("✅ 没有发现孤立的insight记录")
            else:
                print("⚠️ insights表为空或不存在")
        except Exception as e:
            print(f"❌ 检查insights表失败: {e}")
        
        # 5. 检查insight_tags表中的孤立记录
        print("\n📋 步骤5: 检查insight_tags表中的孤立记录...")
        try:
            insight_tags_response = supabase.table('insight_tags').select('user_id').execute()
            if hasattr(insight_tags_response, 'data') and insight_tags_response.data:
                insight_tag_user_ids = [tag.get('user_id') for tag in insight_tags_response.data if tag.get('user_id')]
                print(f"✅ 找到 {len(insight_tag_user_ids)} 个insight_tag记录")
                
                # 找出孤立的insight_tag记录
                orphaned_insight_tags = [uid for uid in insight_tag_user_ids if uid not in auth_user_ids]
                if orphaned_insight_tags:
                    print(f"⚠️ 发现 {len(orphaned_insight_tags)} 个孤立的insight_tag记录")
                    print(f"孤立记录用户ID: {orphaned_insight_tags[:5]}...")
                    
                    # 询问是否删除
                    response = input(f"\n是否删除这 {len(orphaned_insight_tags)} 个孤立的insight_tag记录？(y/N): ")
                    if response.lower() == 'y':
                        for orphaned_uid in orphaned_insight_tags:
                            try:
                                supabase.table('insight_tags').delete().eq('user_id', orphaned_uid).execute()
                                print(f"✅ 已删除孤立insight_tag: {orphaned_uid}")
                            except Exception as e:
                                print(f"❌ 删除insight_tag {orphaned_uid} 失败: {e}")
                else:
                    print("✅ 没有发现孤立的insight_tag记录")
            else:
                print("⚠️ insight_tags表为空或不存在")
        except Exception as e:
            print(f"❌ 检查insight_tags表失败: {e}")
        
        print("\n🏁 数据清理完成")
        print("\n💡 建议:")
        print("1. 现在可以尝试重新注册用户")
        print("2. 如果还有问题，检查Supabase项目的RLS策略")
        print("3. 确保.env文件中的SUPABASE_SERVICE_ROLE_KEY没有换行符")
        
    except Exception as e:
        print(f"❌ 清理数据时出错: {e}")

if __name__ == "__main__":
    print("🧹 孤立数据清理工具")
    print("=" * 50)
    print("⚠️  警告: 此工具将删除孤立的数据记录")
    print("⚠️  请确保你已经备份了重要数据")
    print("=" * 50)
    
    response = input("是否继续？(y/N): ")
    if response.lower() == 'y':
        cleanup_orphaned_data()
    else:
        print("操作已取消")


