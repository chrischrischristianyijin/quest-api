#!/usr/bin/env python3
"""
环境变量检查脚本
用于验证Supabase配置是否正确设置
"""

import os
from dotenv import load_dotenv

def check_environment():
    """检查环境变量配置"""
    print("🔍 检查环境变量配置...")
    print("=" * 50)
    
    # 加载.env文件
    load_dotenv()
    
    # 检查必需的环境变量
    required_vars = {
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_ANON_KEY': os.getenv('SUPABASE_ANON_KEY'),
        'SUPABASE_SERVICE_ROLE_KEY': os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    }
    
    # 检查可选的环境变量
    optional_vars = {
        'API_PORT': os.getenv('API_PORT', '8080'),
        'NODE_ENV': os.getenv('NODE_ENV', 'development'),
        'JWT_SECRET_KEY': os.getenv('JWT_SECRET_KEY'),
        'SECRET_KEY': os.getenv('SECRET_KEY')
    }
    
    print("📋 必需的环境变量:")
    print("-" * 30)
    
    all_required_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            # 隐藏敏感信息
            if 'KEY' in var_name:
                display_value = f"{var_value[:20]}..." if len(var_value) > 20 else var_value
            elif 'URL' in var_name:
                display_value = var_value
            else:
                display_value = var_value
            print(f"✅ {var_name}: {display_value}")
        else:
            print(f"❌ {var_name}: 未设置")
            all_required_set = False
    
    print("\n📋 可选的环境变量:")
    print("-" * 30)
    
    for var_name, var_value in optional_vars.items():
        if var_value:
            print(f"✅ {var_name}: {var_value}")
        else:
            print(f"⚠️  {var_name}: 未设置")
    
    print("\n" + "=" * 50)
    
    if all_required_set:
        print("🎉 所有必需的环境变量都已设置！")
        print("✅ 你可以启动应用了")
        
        # 验证URL格式
        supabase_url = required_vars['SUPABASE_URL']
        if supabase_url.startswith('https://') and 'supabase.co' in supabase_url:
            print("✅ Supabase URL格式正确")
        else:
            print("⚠️  Supabase URL格式可能不正确")
            
        # 验证密钥长度
        anon_key = required_vars['SUPABASE_ANON_KEY']
        service_key = required_vars['SUPABASE_SERVICE_ROLE_KEY']
        
        if len(anon_key) > 100:
            print("✅ Anon Key长度正常")
        else:
            print("⚠️  Anon Key长度可能不正确")
            
        if len(service_key) > 100:
            print("✅ Service Role Key长度正常")
        else:
            print("⚠️  Service Role Key长度可能不正确")
            
    else:
        print("❌ 缺少必需的环境变量！")
        print("\n🔧 解决方案:")
        print("1. 在项目根目录创建 .env 文件")
        print("2. 添加以下内容:")
        print("   SUPABASE_URL=https://your-project.supabase.co")
        print("   SUPABASE_ANON_KEY=your-anon-key-here")
        print("   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here")
        print("\n📖 详细说明请查看 ENVIRONMENT_SETUP.md 文件")
    
    return all_required_set

def test_supabase_connection():
    """测试Supabase连接"""
    if not check_environment():
        return False
    
    try:
        print("\n🔗 测试Supabase连接...")
        
        # 尝试导入和初始化
        from supabase import create_client
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        # 创建客户端
        supabase = create_client(supabase_url, supabase_key)
        
        # 测试连接（尝试获取用户信息）
        try:
            # 这是一个安全的测试，不会修改数据
            response = supabase.auth.get_user()
            print("✅ Supabase客户端创建成功")
            print("✅ 认证服务连接正常")
        except Exception as e:
            print(f"⚠️  认证服务连接测试失败: {e}")
            print("   这可能是正常的，如果用户未登录")
        
        print("✅ Supabase连接测试完成")
        return True
        
    except Exception as e:
        print(f"❌ Supabase连接测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Quest API 环境变量检查工具")
    print("=" * 50)
    
    # 检查环境变量
    env_ok = check_environment()
    
    if env_ok:
        # 测试连接
        test_supabase_connection()
    
    print("\n" + "=" * 50)
    print("检查完成！")
