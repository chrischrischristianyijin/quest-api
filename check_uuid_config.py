#!/usr/bin/env python3
"""
检查数据库UUID配置的脚本
确保所有表的UUID字段都配置为自动生成
"""

import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class UUIDConfigChecker:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_service_key:
            raise ValueError("缺少必需的Supabase环境变量")
        
        self.supabase = create_client(self.supabase_url, self.supabase_service_key)
        logger.info("✅ Supabase客户端初始化成功")
    
    async def check_table_uuid_config(self):
        """检查所有表的UUID配置"""
        logger.info("🔍 检查数据库表UUID配置...")
        
        # 需要检查的表
        tables_to_check = [
            'profiles',
            'insights', 
            'user_tags',
            'insight_tags'
        ]
        
        for table_name in tables_to_check:
            try:
                logger.info(f"\n📋 检查表: {table_name}")
                
                # 获取表结构信息
                response = self.supabase.rpc('get_table_info', {'table_name': table_name}).execute()
                
                if hasattr(response, 'data') and response.data:
                    table_info = response.data
                    logger.info(f"表结构: {table_info}")
                else:
                    # 尝试直接查询表
                    try:
                        sample_response = self.supabase.table(table_name).select('*').limit(1).execute()
                        if sample_response.data:
                            sample_data = sample_response.data[0]
                            logger.info(f"✅ 表 {table_name} 存在，示例数据: {sample_data}")
                            
                            # 检查ID字段类型
                            if 'id' in sample_data:
                                id_value = sample_data['id']
                                logger.info(f"ID字段值: {id_value} (类型: {type(id_value)})")
                                
                                # 检查是否为UUID格式
                                if isinstance(id_value, str) and len(id_value) == 36:
                                    logger.info(f"✅ {table_name}.id 字段格式正确 (UUID)")
                                else:
                                    logger.warning(f"⚠️ {table_name}.id 字段格式异常: {id_value}")
                            else:
                                logger.warning(f"⚠️ 表 {table_name} 没有id字段")
                        else:
                            logger.info(f"表 {table_name} 存在但无数据")
                    except Exception as e:
                        logger.error(f"查询表 {table_name} 失败: {e}")
                
            except Exception as e:
                logger.error(f"检查表 {table_name} 配置失败: {e}")
    
    async def test_uuid_generation(self):
        """测试UUID自动生成功能"""
        logger.info("\n🧪 测试UUID自动生成...")
        
        try:
            # 测试insights表
            logger.info("测试insights表UUID自动生成...")
            test_insight = {
                "title": "UUID测试",
                "description": "测试UUID自动生成",
                "user_id": "00000000-0000-0000-0000-000000000000",  # 测试用户ID
                "created_at": "2024-01-01T00:00:00.000Z",
                "updated_at": "2024-01-01T00:00:00.000Z"
            }
            
            response = self.supabase.table('insights').insert(test_insight).execute()
            if response.data:
                generated_id = response.data[0]['id']
                logger.info(f"✅ insights表UUID自动生成成功: {generated_id}")
                
                # 清理测试数据
                self.supabase.table('insights').delete().eq('id', generated_id).execute()
                logger.info("✅ 测试数据已清理")
            else:
                logger.error("❌ insights表UUID自动生成失败")
        
        except Exception as e:
            logger.error(f"测试UUID自动生成失败: {e}")
    
    async def check_database_constraints(self):
        """检查数据库约束"""
        logger.info("\n🔒 检查数据库约束...")
        
        try:
            # 检查profiles表的外键约束
            logger.info("检查profiles表外键约束...")
            
            # 尝试插入一个不存在的user_id
            test_profile = {
                "id": "99999999-9999-9999-9999-999999999999",
                "nickname": "测试用户",
                "created_at": "2024-01-01T00:00:00.000Z",
                "updated_at": "2024-01-01T00:00:00.000Z"
            }
            
            try:
                response = self.supabase.table('profiles').insert(test_profile).execute()
                if response.data:
                    logger.warning("⚠️ profiles表外键约束可能缺失")
                    # 清理测试数据
                    self.supabase.table('profiles').delete().eq('id', test_profile['id']).execute()
                else:
                    logger.info("✅ profiles表外键约束正常")
            except Exception as e:
                if "foreign key" in str(e).lower():
                    logger.info("✅ profiles表外键约束正常")
                else:
                    logger.error(f"检查外键约束时出错: {e}")
        
        except Exception as e:
            logger.error(f"检查数据库约束失败: {e}")

async def main():
    """主函数"""
    try:
        logger.info("🚀 启动UUID配置检查工具...")
        
        checker = UUIDConfigChecker()
        
        # 检查表UUID配置
        await checker.check_table_uuid_config()
        
        # 测试UUID自动生成
        await checker.test_uuid_generation()
        
        # 检查数据库约束
        await checker.check_database_constraints()
        
        logger.info("\n🎉 UUID配置检查完成！")
        
    except Exception as e:
        logger.error(f"❌ 检查过程出错: {e}")

if __name__ == "__main__":
    asyncio.run(main())
