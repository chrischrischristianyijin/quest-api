#!/usr/bin/env python3
"""
测试auth修复的简单脚本
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_env_vars():
    """测试环境变量是否正确加载"""
    print("🔍 检查环境变量...")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    print(f"SUPABASE_URL: {'✅ 已设置' if supabase_url else '❌ 未设置'}")
    print(f"SUPABASE_ANON_KEY: {'✅ 已设置' if supabase_anon_key else '❌ 未设置'}")
    print(f"SUPABASE_SERVICE_ROLE_KEY: {'✅ 已设置' if supabase_service_key else '❌ 未设置'}")
    
    if supabase_service_key:
        print(f"Service Key 长度: {len(supabase_service_key)}")
        print(f"Service Key 前50字符: {supabase_service_key[:50]}...")
    
    return all([supabase_url, supabase_anon_key, supabase_service_key])

def suggest_fix():
    """建议修复方案"""
    print("\n🔧 修复建议:")
    print("1. 检查 .env 文件中的 SUPABASE_SERVICE_ROLE_KEY 是否完整")
    print("2. 确保没有换行符分割密钥")
    print("3. 重启应用以重新加载环境变量")
    print("4. 如果问题持续，检查 Supabase 项目设置")

if __name__ == "__main__":
    print("🧪 测试环境变量配置")
    print("=" * 40)
    
    success = test_env_vars()
    
    if success:
        print("\n✅ 环境变量配置正确")
        print("现在可以运行 check_table_structure.py 来检查数据库表结构")
    else:
        print("\n❌ 环境变量配置有问题")
        suggest_fix()
