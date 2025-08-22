#!/usr/bin/env python3
"""
Render部署环境变量检查脚本
专门用于检查Render平台上的环境变量配置
"""

import os
from dotenv import load_dotenv

def check_render_environment():
    """检查Render环境变量配置"""
    print("🔍 检查Render环境变量配置...")
    print("=" * 60)
    
    # 加载.env文件（如果存在）
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
    print("-" * 40)
    
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
    print("-" * 40)
    
    for var_name, var_value in optional_vars.items():
        if var_value:
            print(f"✅ {var_name}: {var_value}")
        else:
            print(f"⚠️  {var_name}: 未设置")
    
    print("\n" + "=" * 60)
    
    if all_required_set:
        print("🎉 所有必需的环境变量都已设置！")
        print("✅ 应用应该可以正常启动")
        
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
        print("\n🔧 Render平台配置步骤:")
        print("1. 登录Render控制台: https://dashboard.render.com")
        print("2. 选择你的Web Service")
        print("3. 点击 'Environment' 标签")
        print("4. 添加以下环境变量:")
        print("   SUPABASE_URL=https://your-project.supabase.co")
        print("   SUPABASE_ANON_KEY=your-anon-key-here")
        print("   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here")
        print("5. 点击 'Save Changes'")
        print("6. 重新部署服务")
    
    return all_required_set

def check_settings_config():
    """检查settings配置"""
    print("\n🔧 检查应用配置...")
    print("-" * 40)
    
    try:
        from app.core.config import settings
        
        print(f"✅ 配置文件加载成功")
        print(f"✅ SUPABASE_URL: {settings.SUPABASE_URL[:50] if settings.SUPABASE_URL else '未设置'}...")
        print(f"✅ SUPABASE_ANON_KEY: {'已设置' if settings.SUPABASE_ANON_KEY else '未设置'}")
        print(f"✅ SUPABASE_SERVICE_ROLE_KEY: {'已设置' if settings.SUPABASE_SERVICE_ROLE_KEY else '未设置'}")
        
        return True
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False

def test_supabase_connection():
    """测试Supabase连接"""
    if not check_render_environment():
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

def check_render_specific_issues():
    """检查Render特定的问题"""
    print("\n🔍 检查Render特定问题...")
    print("-" * 40)
    
    # 检查是否在Render环境
    is_render = os.getenv('RENDER') == 'true'
    print(f"🌐 Render环境: {'是' if is_render else '否'}")
    
    # 检查端口配置
    port = os.getenv('PORT') or os.getenv('API_PORT') or '8080'
    print(f"🔌 端口配置: {port}")
    
    # 检查环境
    env = os.getenv('NODE_ENV') or os.getenv('ENVIRONMENT') or 'development'
    print(f"🏭 环境: {env}")
    
    # 检查是否有其他Supabase相关的环境变量
    supabase_vars = [k for k in os.environ.keys() if 'SUPABASE' in k]
    print(f"📦 Supabase相关环境变量: {len(supabase_vars)} 个")
    for var in supabase_vars:
        value = os.getenv(var)
        if 'KEY' in var:
            display_value = f"{value[:20]}..." if value and len(value) > 20 else value
        else:
            display_value = value
        print(f"  {var}: {display_value}")

if __name__ == "__main__":
    print("🚀 Quest API Render环境检查工具")
    print("=" * 60)
    
    # 检查环境变量
    env_ok = check_render_environment()
    
    # 检查应用配置
    config_ok = check_settings_config()
    
    # 检查Render特定问题
    check_render_specific_issues()
    
    if env_ok and config_ok:
        # 测试连接
        test_supabase_connection()
    
    print("\n" + "=" * 60)
    print("检查完成！")
    
    if not env_ok:
        print("\n💡 建议:")
        print("1. 检查Render平台的环境变量设置")
        print("2. 确保环境变量名称完全正确（区分大小写）")
        print("3. 重新部署服务以应用新的环境变量")
        print("4. 检查Render服务的日志输出")
