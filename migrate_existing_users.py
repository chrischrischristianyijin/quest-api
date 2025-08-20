#!/usr/bin/env python3
"""
数据迁移脚本：将现有的users表数据迁移到Supabase Auth架构
保留现有用户数据，同时使用新的认证系统
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

def get_supabase_client() -> Client:
    """获取Supabase客户端"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        print("❌ 缺少必要的环境变量")
        print("请确保设置了 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    
    return create_client(url, key)

def check_existing_users_table(supabase: Client):
    """检查现有的users表"""
    print("🔍 检查现有的users表...")
    
    try:
        # 尝试查询现有的users表
        response = supabase.table("users").select("*").limit(5).execute()
        
        if response.data:
            print(f"✅ 找到现有users表，包含 {len(response.data)} 条记录")
            print("📋 表结构:")
            for key in response.data[0].keys():
                print(f"  - {key}")
            return response.data
        else:
            print("ℹ️ users表存在但没有数据")
            return []
            
    except Exception as e:
        print(f"❌ 查询users表失败: {e}")
        return None

def create_user_profiles_table(supabase: Client):
    """创建user_profiles表"""
    print("🔧 创建user_profiles表...")
    
    try:
        # 创建user_profiles表的SQL
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS user_profiles (
            id UUID REFERENCES auth.users(id) PRIMARY KEY,
            nickname TEXT,
            avatar_url TEXT,
            bio TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
        
        # 执行SQL
        result = supabase.rpc('exec_sql', {'sql': create_table_sql})
        print("✅ user_profiles表创建成功")
        return True
        
    except Exception as e:
        print(f"⚠️ 创建表失败，可能已存在: {e}")
        return True

def migrate_user_data(supabase: Client, existing_users):
    """迁移用户数据"""
    print(f"🔄 开始迁移 {len(existing_users)} 个用户...")
    
    migrated_count = 0
    failed_count = 0
    
    for user in existing_users:
        try:
            email = user.get('email')
            if not email:
                print(f"⚠️ 跳过没有邮箱的用户: {user}")
                continue
            
            print(f"🔄 迁移用户: {email}")
            
            # 1. 检查用户是否已在Supabase Auth中
            try:
                # 尝试获取现有用户
                auth_user = supabase.auth.admin.list_users()
                existing_auth_user = next((u for u in auth_user.users if u.email == email), None)
                
                if existing_auth_user:
                    print(f"  ✅ 用户已在Supabase Auth中: {existing_auth_user.id}")
                    user_id = existing_auth_user.id
                else:
                    print(f"  ⚠️ 用户不在Supabase Auth中，需要手动创建")
                    print(f"  📧 请手动在Supabase控制台创建用户: {email}")
                    continue
                    
            except Exception as e:
                print(f"  ❌ 检查Supabase Auth用户失败: {e}")
                continue
            
            # 2. 迁移用户资料到user_profiles表
            profile_data = {
                "id": user_id,
                "nickname": user.get('nickname') or user.get('username'),
                "avatar_url": user.get('avatar_url'),
                "bio": user.get('bio'),
                "created_at": user.get('created_at') or "2024-01-01T00:00:00.000Z",
                "updated_at": user.get('updated_at') or "2024-01-01T00:00:00.000Z"
            }
            
            # 插入或更新用户资料
            try:
                result = supabase.table("user_profiles").upsert(profile_data).execute()
                print(f"  ✅ 用户资料迁移成功")
                migrated_count += 1
                
            except Exception as e:
                print(f"  ❌ 用户资料迁移失败: {e}")
                failed_count += 1
                
        except Exception as e:
            print(f"❌ 迁移用户 {email} 时出错: {e}")
            failed_count += 1
    
    print(f"\n🎉 迁移完成！")
    print(f"✅ 成功迁移: {migrated_count} 个用户")
    print(f"❌ 迁移失败: {failed_count} 个用户")
    
    return migrated_count, failed_count

def create_migration_summary(existing_users, migrated_count, failed_count):
    """创建迁移总结"""
    print("\n" + "="*60)
    print("📊 数据迁移总结")
    print("="*60)
    
    print(f"📋 现有用户总数: {len(existing_users)}")
    print(f"✅ 成功迁移: {migrated_count}")
    print(f"❌ 迁移失败: {failed_count}")
    
    if failed_count > 0:
        print("\n⚠️ 注意事项:")
        print("1. 失败的迁移需要手动处理")
        print("2. 检查Supabase Auth中是否已存在对应用户")
        print("3. 确保所有必要的字段都已正确映射")
    
    print("\n🔧 后续步骤:")
    print("1. 在Supabase控制台检查user_profiles表")
    print("2. 测试用户登录功能")
    print("3. 更新业务逻辑使用新的表结构")
    print("4. 考虑删除旧的users表（备份后）")

def main():
    """主函数"""
    print("🚀 Quest API 用户数据迁移工具")
    print("=" * 60)
    
    # 检查环境变量
    required_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
        print("请检查.env文件")
        sys.exit(1)
    
    print("✅ 环境变量检查通过")
    
    try:
        # 获取Supabase客户端
        supabase = get_supabase_client()
        
        # 检查现有用户表
        existing_users = check_existing_users_table(supabase)
        
        if not existing_users:
            print("ℹ️ 没有现有用户数据需要迁移")
            return
        
        # 创建user_profiles表
        create_user_profiles_table(supabase)
        
        print("\n" + "="*60)
        
        # 询问是否继续
        response = input("是否继续执行数据迁移？(y/N): ").strip().lower()
        
        if response in ['y', 'yes']:
            # 执行迁移
            migrated_count, failed_count = migrate_user_data(supabase, existing_users)
            
            # 创建迁移总结
            create_migration_summary(existing_users, migrated_count, failed_count)
        else:
            print("❌ 取消迁移")
            
    except Exception as e:
        print(f"❌ 迁移过程中出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
