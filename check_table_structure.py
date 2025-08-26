#!/usr/bin/env python3
"""
检查数据库表结构的脚本
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 加载环境变量
load_dotenv()

def check_table_structure():
    """检查数据库表结构"""
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
        
        print("🔍 检查数据库表结构...")
        
        # 检查profiles表结构
        try:
            print("\n📋 检查 profiles 表结构...")
            response = supabase.table('profiles').select('*').limit(1).execute()
            
            if hasattr(response, 'data') and response.data:
                print("✅ profiles 表存在且有数据")
                # 获取第一条记录的字段
                first_record = response.data[0]
                print(f"字段列表: {list(first_record.keys())}")
                
                # 检查关键字段
                if 'id' in first_record:
                    print(f"✅ id 字段存在，类型: {type(first_record['id'])}")
                if 'user_id' in first_record:
                    print(f"✅ user_id 字段存在，类型: {type(first_record['user_id'])}")
                if 'nickname' in first_record:
                    print(f"✅ nickname 字段存在，类型: {type(first_record['nickname'])}")
                    
            else:
                print("⚠️ profiles 表存在但无数据")
                
        except Exception as e:
            print(f"❌ 检查 profiles 表失败: {e}")
        
        # 检查user_tags表结构
        try:
            print("\n📋 检查 user_tags 表结构...")
            response = supabase.table('user_tags').select('*').limit(1).execute()
            
            if hasattr(response, 'data') and response.data:
                print("✅ user_tags 表存在且有数据")
                first_record = response.data[0]
                print(f"字段列表: {list(first_record.keys())}")
            else:
                print("⚠️ user_tags 表存在但无数据")
                
        except Exception as e:
            print(f"❌ 检查 user_tags 表失败: {e}")
        
        # 检查insights表结构
        try:
            print("\n📋 检查 insights 表结构...")
            response = supabase.table('insights').select('*').limit(1).execute()
            
            if hasattr(response, 'data') and response.data:
                print("✅ insights 表存在且有数据")
                first_record = response.data[0]
                print(f"字段列表: {list(first_record.keys())}")
            else:
                print("⚠️ insights 表存在但无数据")
                
        except Exception as e:
            print(f"❌ 检查 insights 表失败: {e}")
        
        # 检查insight_tags表结构
        try:
            print("\n📋 检查 insight_tags 表结构...")
            response = supabase.table('insight_tags').select('*').limit(1).execute()
            
            if hasattr(response, 'data') and response.data:
                print("✅ insight_tags 表存在且有数据")
                first_record = response.data[0]
                print(f"字段列表: {list(first_record.keys())}")
            else:
                print("⚠️ insight_tags 表存在但无数据")
                
        except Exception as e:
            print(f"❌ 检查 insight_tags 表失败: {e}")
        
        # 检查auth.users表（通过RPC）
        try:
            print("\n📋 检查 auth.users 表...")
            # 尝试获取一个用户
            response = supabase.auth.admin.list_users()
            if hasattr(response, 'data') and response.data:
                print("✅ auth.users 表可访问")
                first_user = response.data[0]
                print(f"用户字段: {list(first_user.keys())}")
            else:
                print("⚠️ auth.users 表可访问但无数据")
                
        except Exception as e:
            print(f"❌ 检查 auth.users 表失败: {e}")
        
        print("\n🏁 表结构检查完成")
        
    except Exception as e:
        print(f"❌ 检查表结构时出错: {e}")

if __name__ == "__main__":
    check_table_structure()


