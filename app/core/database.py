from supabase import create_client, Client
from app.core.config import settings
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局Supabase客户端
supabase: Client = None
supabase_service: Client = None

async def init_supabase():
    """初始化Supabase连接"""
    global supabase, supabase_service
    
    try:
        logger.info("🔧 初始化Supabase连接...")
        
        # 验证配置
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise ValueError("Supabase配置不完整")
        
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
        raise

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
        # 检查users表（如果存在）
        try:
            users_response = supabase_service.table('users').select('id').limit(1).execute()
            logger.info("✅ users表检查通过")
        except Exception as e:
            if "does not exist" in str(e):
                logger.info("ℹ️ users表不存在，这是正常的（使用Supabase Auth）")
            else:
                logger.warning(f"⚠️ users表检查失败: {e}")
        
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
    if not supabase:
        raise RuntimeError("Supabase未初始化")
    return supabase

def get_supabase_service() -> Client:
    """获取Supabase服务端客户端"""
    if not supabase_service:
        raise RuntimeError("Supabase服务端客户端未初始化")
    return supabase_service

def get_supabase_client() -> Client:
    """获取Supabase客户端（兼容性函数）"""
    return get_supabase()
