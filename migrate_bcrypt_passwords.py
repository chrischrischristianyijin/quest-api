#!/usr/bin/env python3
"""
数据库迁移脚本：处理已有的bcrypt密码
将已有的bcrypt加密密码迁移到新的用户认证系统
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
from passlib.context import CryptContext

# 加载环境变量
load_dotenv()

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_supabase_client() -> Client:
    """获取Supabase客户端"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        print("❌ 缺少必要的环境变量")
        print("请确保设置了 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    
    return create_client(url, key)

def migrate_bcrypt_passwords():
    """迁移bcrypt密码"""
    print("🔄 开始迁移bcrypt密码...")
    
    try:
        supabase = get_supabase_client()
        
        # 获取所有用户
        print("📋 获取用户列表...")
        response = supabase.table("users").select("*").execute()
        
        if not response.data:
            print("ℹ️ 没有找到用户数据")
            return
        
        print(f"📊 找到 {len(response.data)} 个用户")
        
        migrated_count = 0
        for user in response.data:
            user_id = user.get('id')
            email = user.get('email')
            password_hash = user.get('password_hash')
            
            if not password_hash:
                print(f"⚠️ 用户 {email} 没有密码哈希，跳过")
                continue
            
            # 检查是否是bcrypt格式
            if password_hash.startswith('$2b$') or password_hash.startswith('$2a$'):
                print(f"🔄 迁移用户 {email} 的bcrypt密码...")
                
                try:
                    # 更新用户记录，确保密码哈希字段存在
                    update_data = {
                        "password_hash": password_hash,
                        "updated_at": "2024-01-01T00:00:00.000Z"
                    }
                    
                    # 如果users表没有password_hash字段，先添加
                    # 这里需要手动在Supabase中添加password_hash字段
                    
                    result = supabase.table("users").update(update_data).eq("id", user_id).execute()
                    
                    if result.data:
                        print(f"✅ 用户 {email} 密码迁移成功")
                        migrated_count += 1
                    else:
                        print(f"❌ 用户 {email} 密码迁移失败")
                        
                except Exception as e:
                    print(f"❌ 迁移用户 {email} 时出错: {e}")
            else:
                print(f"ℹ️ 用户 {email} 的密码不是bcrypt格式，跳过")
        
        print(f"\n🎉 密码迁移完成！成功迁移 {migrated_count} 个用户")
        
    except Exception as e:
        print(f"❌ 迁移过程中出错: {e}")
        sys.exit(1)

def check_database_structure():
    """检查数据库结构"""
    print("🔍 检查数据库结构...")
    
    try:
        supabase = get_supabase_client()
        
        # 检查users表结构
        response = supabase.table("users").select("id, email, created_at").limit(1).execute()
        
        if response.data:
            print("✅ users表存在")
            
            # 获取表结构信息
            user = response.data[0]
            print(f"📋 用户表字段: {list(user.keys())}")
            
            # 检查是否有password_hash字段
            if 'password_hash' in user:
                print("✅ password_hash字段存在")
            else:
                print("⚠️ password_hash字段不存在，需要手动添加")
                print("请在Supabase控制台中为users表添加password_hash字段（类型：text）")
        else:
            print("❌ users表不存在或为空")
            
    except Exception as e:
        print(f"❌ 检查数据库结构时出错: {e}")

def main():
    """主函数"""
    print("🚀 Quest API 密码迁移工具")
    print("=" * 50)
    
    # 检查环境变量
    required_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
        print("请检查.env文件")
        sys.exit(1)
    
    print("✅ 环境变量检查通过")
    
    # 检查数据库结构
    check_database_structure()
    
    print("\n" + "=" * 50)
    
    # 询问是否继续
    response = input("是否继续执行密码迁移？(y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        migrate_bcrypt_passwords()
    else:
        print("❌ 取消迁移")
        sys.exit(0)

if __name__ == "__main__":
    main()
