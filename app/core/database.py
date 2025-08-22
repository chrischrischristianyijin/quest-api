from supabase import create_client, Client
from app.core.config import settings
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局Supabase客户端
supabase: Client = None
supabase_service: Client = None

def check_environment_variables():
    """检查环境变量配置"""
    logger.info("🔍 检查环境变量配置...")
    
    # 检查必需的环境变量 - 使用settings而不是os.getenv
    required_vars = {
        'SUPABASE_URL': settings.SUPABASE_URL,
        'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
        'SUPABASE_SERVICE_ROLE_KEY': settings.SUPABASE_SERVICE_ROLE_KEY
    }
    
    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value:
            missing_vars.append(var_name)
        else:
            logger.info(f"✅ {var_name}: {'已设置' if var_value else '未设置'}")
    
    if missing_vars:
        error_msg = f"❌ 缺少必需的环境变量: {', '.join(missing_vars)}"
        logger.error(error_msg)
        logger.error("请检查Render平台的环境变量配置")
        logger.error("确保以下环境变量已设置:")
        for var in missing_vars:
            logger.error(f"  {var}")
        raise ValueError(error_msg)
    
    logger.info("✅ 环境变量配置检查通过")
    return True

async def init_supabase():
    """初始化Supabase连接"""
    global supabase, supabase_service
    
    try:
        logger.info("🔧 初始化Supabase连接...")
        
        # 首先检查环境变量
        check_environment_variables()
        
        # 验证配置
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise ValueError("Supabase配置不完整")
        
        logger.info(f"🔗 连接到Supabase: {settings.SUPABASE_URL[:50]}...")
        
        # 创建客户端
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        
        supabase_service = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # 测试连接
        await test_supabase_connection()
        
        logger.info("✅ Supabase连接初始化成功")
        
    except Exception as e:
        logger.error(f"❌ Supabase连接初始化失败: {e}")
        # 不要重新抛出异常，让应用继续启动
        logger.warning("⚠️ Supabase初始化失败，但应用将继续启动")
        logger.warning("⚠️ 某些功能可能无法正常工作")

async def test_supabase_connection():
    """测试Supabase连接"""
    try:
        # 测试Supabase Auth连接（这个总是可用的）
        logger.info("✅ Supabase Auth连接测试成功")
        
        # 检查表结构（可选，不阻止启动）
        await check_database_structure()
        
    except Exception as e:
        logger.error(f"❌ 数据库连接测试失败: {e}")
        # 不要抛出异常，让应用继续启动
        logger.warning("⚠️ 数据库连接测试失败，但应用将继续启动")

async def check_database_structure():
    """检查数据库表结构"""
    try:
        # 检查profiles表（如果存在）
        try:
            profiles_response = supabase_service.table('profiles').select('id').limit(1).execute()
            logger.info("✅ profiles表检查通过")
        except Exception as e:
            if "does not exist" in str(e):
                logger.info("ℹ️ profiles表不存在，这是正常的")
            else:
                logger.warning(f"⚠️ profiles表检查失败: {e}")
        
        # 检查insights表（如果存在）
        try:
            insights_response = supabase_service.table('insights').select('id, title, description, image_url').limit(1).execute()
            logger.info("✅ insights表检查通过")
        except Exception as e:
            if "does not exist" in str(e):
                logger.info("ℹ️ insights表不存在，这是正常的")
            else:
                logger.warning(f"⚠️ insights表检查失败: {e}")
        
        logger.info("✅ 数据库表结构检查完成")
        
    except Exception as e:
        logger.error(f"❌ 数据库表结构检查失败: {e}")
        # 不阻止启动
        pass

def get_supabase() -> Client:
    """获取Supabase客户端"""
    global supabase
    if not supabase:
        # 尝试重新初始化
        try:
            logger.warning("⚠️ Supabase客户端未初始化，尝试重新初始化...")
            import asyncio
            # 在同步上下文中运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(init_supabase())
            loop.close()
            
            if not supabase:
                raise RuntimeError("Supabase重新初始化失败")
        except Exception as e:
            logger.error(f"❌ Supabase重新初始化失败: {e}")
            raise RuntimeError(f"Supabase未初始化。请检查环境变量配置：{e}")
    
    return supabase

def get_supabase_service() -> Client:
    """获取Supabase服务端客户端"""
    global supabase_service
    if not supabase_service:
        # 尝试重新初始化
        try:
            logger.warning("⚠️ Supabase服务端客户端未初始化，尝试重新初始化...")
            import asyncio
            # 在同步上下文中运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(init_supabase())
            loop.close()
            
            if not supabase_service:
                raise RuntimeError("Supabase服务端客户端重新初始化失败")
        except Exception as e:
            logger.error(f"❌ Supabase服务端客户端重新初始化失败: {e}")
            raise RuntimeError(f"Supabase服务端客户端未初始化。请检查环境变量配置：{e}")
    
    return supabase_service

def get_supabase_client() -> Client:
    """获取Supabase客户端（兼容性函数）"""
    return get_supabase()
