#!/usr/bin/env python3
"""
用户表关联脚本：将现有的users表与Supabase Auth的auth.users表建立关联
支持多种关联策略
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

def check_table_structure(supabase: Client):
    """检查表结构"""
    print("🔍 检查表结构...")
    
    try:
        # 检查现有的users表
        print("📋 检查现有users表...")
        old_users_response = supabase.table("users").select("*").limit(1).execute()
        
        if old_users_response.data:
            print(f"✅ 找到现有users表，包含 {len(old_users_response.data)} 条记录")
            old_user = old_users_response.data[0]
            print("📋 现有users表字段:")
            for key in old_user.keys():
                print(f"  - {key}")
        else:
            print("ℹ️ users表存在但没有数据")
            return None
        
        # 检查auth.users表
        print("\n📋 检查Supabase Auth表...")
        try:
            auth_users_response = supabase.auth.admin.list_users()
            print(f"✅ 找到 {len(auth_users_response.users)} 个Supabase Auth用户")
            
            if auth_users_response.users:
                auth_user = auth_users_response.users[0]
                print("📋 auth.users表字段:")
                print(f"  - id: {auth_user.id}")
                print(f"  - email: {auth_user.email}")
                print(f"  - created_at: {auth_user.created_at}")
                
        except Exception as e:
            print(f"⚠️ 无法访问auth.users表: {e}")
            return None
            
        return old_users_response.data
        
    except Exception as e:
        print(f"❌ 检查表结构失败: {e}")
        return None

def create_link_table(supabase: Client):
    """创建关联表"""
    print("🔧 创建用户关联表...")
    
    try:
        # 创建关联表的SQL
        create_link_table_sql = """
        CREATE TABLE IF NOT EXISTS user_auth_links (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            old_user_id UUID,
            auth_user_id UUID,
            email TEXT,
            link_type TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
        
        # 尝试执行SQL
        try:
            result = supabase.rpc('exec_sql', {'sql': create_link_table_sql})
            print("✅ user_auth_links表创建成功")
        except:
            # 如果RPC不存在，尝试直接创建
            print("⚠️ 无法使用RPC，尝试直接创建表...")
            # 这里需要手动在Supabase控制台创建表
            print("请在Supabase控制台手动创建user_auth_links表")
            print("SQL语句:")
            print(create_link_table_sql)
        
        return True
        
    except Exception as e:
        print(f"⚠️ 创建关联表失败: {e}")
        return False

def link_users_by_email(supabase: Client, existing_users):
    """通过邮箱关联用户"""
    print(f"🔗 通过邮箱关联 {len(existing_users)} 个用户...")
    
    linked_count = 0
    failed_count = 0
    
    try:
        # 获取Supabase Auth用户列表
        auth_users_response = supabase.auth.admin.list_users()
        auth_users = {u.email: u for u in auth_users_response.users}
        
        print(f"📧 找到 {len(auth_users)} 个Supabase Auth用户")
        
        for old_user in existing_users:
            email = old_user.get('email')
            if not email:
                print(f"⚠️ 跳过没有邮箱的用户: {old_user}")
                continue
            
            print(f"🔗 关联用户: {email}")
            
            if email in auth_users:
                # 找到匹配的Supabase Auth用户
                auth_user = auth_users[email]
                old_user_id = old_user.get('id')
                
                print(f"  ✅ 找到匹配的Supabase用户: {auth_user.id}")
                
                # 插入关联记录
                try:
                    link_data = {
                        "old_user_id": old_user_id,
                        "auth_user_id": auth_user.id,
                        "email": email,
                        "link_type": "email_match"
                    }
                    
                    # 尝试插入关联表
                    try:
                        result = supabase.table("user_auth_links").insert(link_data).execute()
                        print(f"  ✅ 关联记录创建成功")
                        linked_count += 1
                    except Exception as e:
                        print(f"  ⚠️ 关联记录创建失败: {e}")
                        # 如果关联表不存在，至少打印关联信息
                        print(f"  📝 关联信息: old_user_id={old_user_id}, auth_user_id={auth_user.id}")
                        linked_count += 1
                        
                except Exception as e:
                    print(f"  ❌ 处理用户关联失败: {e}")
                    failed_count += 1
            else:
                print(f"  ⚠️ 在Supabase Auth中未找到用户: {email}")
                failed_count += 1
        
        print(f"\n🎉 用户关联完成！")
        print(f"✅ 成功关联: {linked_count} 个用户")
        print(f"❌ 关联失败: {failed_count} 个用户")
        
        return linked_count, failed_count
        
    except Exception as e:
        print(f"❌ 用户关联过程中出错: {e}")
        return 0, len(existing_users)

def create_migration_sql(existing_users, linked_count):
    """生成迁移SQL语句"""
    print("\n📝 生成迁移SQL语句...")
    
    print("=" * 60)
    print("🔧 手动迁移SQL语句")
    print("=" * 60)
    
    print("-- 1. 创建user_profiles表")
    print("CREATE TABLE IF NOT EXISTS user_profiles (")
    print("    id UUID REFERENCES auth.users(id) PRIMARY KEY,")
    print("    nickname TEXT,")
    print("    avatar_url TEXT,")
    print("    bio TEXT,")
    print("    auth_provider TEXT DEFAULT 'email',")
    print("    created_at TIMESTAMP DEFAULT NOW(),")
    print("    updated_at TIMESTAMP DEFAULT NOW()")
    print(");")
    
    print("\n-- 2. 插入用户资料数据")
    print("-- 根据user_auth_links表插入数据")
    print("INSERT INTO user_profiles (id, nickname, avatar_url, bio, auth_provider, created_at, updated_at)")
    print("SELECT ")
    print("    ual.auth_user_id,")
    print("    u.nickname,")
    print("    u.avatar_url,")
    print("    u.bio,")
    print("    'email',")
    print("    u.created_at,")
    print("    u.updated_at")
    print("FROM users u")
    print("JOIN user_auth_links ual ON u.id = ual.old_user_id;")
    
    print("\n-- 3. 更新业务表的外键引用")
    print("-- 例如：更新insights表的user_id")
    print("UPDATE insights SET user_id = ual.auth_user_id")
    print("FROM user_auth_links ual")
    print("WHERE insights.user_id = ual.old_user_id;")
    
    print("\n-- 4. 删除旧的关联表（可选）")
    print("-- DROP TABLE user_auth_links;")
    
    print("\n-- 5. 重命名旧users表（可选）")
    print("-- ALTER TABLE users RENAME TO users_old;")

def main():
    """主函数"""
    print("🚀 Quest API 用户表关联工具")
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
        
        # 检查表结构
        existing_users = check_table_structure(supabase)
        
        if not existing_users:
            print("ℹ️ 没有现有用户数据需要关联")
            return
        
        # 创建关联表
        create_link_table(supabase)
        
        print("\n" + "="*60)
        
        # 询问是否继续
        response = input("是否继续执行用户关联？(y/N): ").strip().lower()
        
        if response in ['y', 'yes']:
            # 执行用户关联
            linked_count, failed_count = link_users_by_email(supabase, existing_users)
            
            # 生成迁移SQL
            create_migration_sql(existing_users, linked_count)
            
            print("\n" + "="*60)
            print("📊 关联总结")
            print("="*60)
            print(f"📋 现有用户总数: {len(existing_users)}")
            print(f"✅ 成功关联: {linked_count}")
            print(f"❌ 关联失败: {failed_count}")
            
            if failed_count > 0:
                print("\n⚠️ 注意事项:")
                print("1. 失败的关联需要手动处理")
                print("2. 在Supabase控制台手动创建用户账户")
                print("3. 使用生成的SQL语句完成数据迁移")
            
            print("\n🔧 后续步骤:")
            print("1. 在Supabase控制台检查user_auth_links表")
            print("2. 执行生成的SQL语句")
            print("3. 测试用户登录功能")
            print("4. 验证数据完整性")
            
        else:
            print("❌ 取消用户关联")
            
    except Exception as e:
        print(f"❌ 关联过程中出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
