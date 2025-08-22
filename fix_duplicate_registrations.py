#!/usr/bin/env python3
"""
修复重复注册问题的脚本
清理数据库中已存在的重复注册情况
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

class DuplicateRegistrationFixer:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_service_key:
            raise ValueError("缺少必需的Supabase环境变量")
        
        self.supabase = create_client(self.supabase_url, self.supabase_service_key)
        logger.info("✅ Supabase客户端初始化成功")
    
    async def check_duplicate_registrations(self):
        """检查所有重复注册的情况"""
        logger.info("🔍 检查重复注册情况...")
        
        try:
            # 获取所有auth用户
            auth_users_response = self.supabase.auth.admin.list_users()
            auth_users = auth_users_response.users
            
            logger.info(f"📊 找到 {len(auth_users)} 个auth用户")
            
            duplicates = []
            
            for auth_user in auth_users:
                if not auth_user.email:
                    continue
                    
                # 检查profiles表
                profile_response = self.supabase.table('profiles').select('id').eq('id', auth_user.id).execute()
                profile_exists = bool(profile_response.data)
                
                if not profile_exists:
                    duplicates.append({
                        "email": auth_user.email,
                        "user_id": auth_user.id,
                        "created_at": auth_user.created_at,
                        "auth_exists": True,
                        "profile_exists": False
                    })
            
            logger.info(f"⚠️ 发现 {len(duplicates)} 个重复注册")
            
            return duplicates
            
        except Exception as e:
            logger.error(f"检查重复注册失败: {e}")
            return []
    
    async def fix_duplicate_registration(self, duplicate):
        """修复单个重复注册"""
        try:
            logger.info(f"🔧 修复重复注册: {duplicate['email']}")
            
            # 删除auth用户
            self.supabase.auth.admin.delete_user(duplicate['user_id'])
            logger.info(f"✅ 已删除auth用户: {duplicate['email']}")
            
            return True
            
        except Exception as e:
            logger.error(f"修复重复注册失败 {duplicate['email']}: {e}")
            return False
    
    async def fix_all_duplicates(self):
        """修复所有重复注册"""
        logger.info("🚀 开始修复所有重复注册...")
        
        duplicates = await self.check_duplicate_registrations()
        
        if not duplicates:
            logger.info("✅ 没有发现重复注册，无需修复")
            return
        
        success_count = 0
        fail_count = 0
        
        for duplicate in duplicates:
            logger.info(f"🔧 处理: {duplicate['email']} (ID: {duplicate['user_id']})")
            
            if await self.fix_duplicate_registration(duplicate):
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"🎯 修复完成！成功: {success_count}, 失败: {fail_count}")
        
        # 再次检查
        remaining_duplicates = await self.check_duplicate_registrations()
        if remaining_duplicates:
            logger.warning(f"⚠️ 仍有 {len(remaining_duplicates)} 个重复注册未修复")
        else:
            logger.info("✅ 所有重复注册已修复完成！")
    
    async def create_missing_profiles(self):
        """为有auth用户但没有profile的用户创建profile"""
        logger.info("🔍 检查缺失的profile...")
        
        try:
            # 获取所有auth用户
            auth_users_response = self.supabase.auth.admin.list_users()
            auth_users = auth_users_response.users
            
            missing_profiles = []
            
            for auth_user in auth_users:
                if not auth_user.email:
                    continue
                
                # 检查profiles表
                profile_response = self.supabase.table('profiles').select('id').eq('id', auth_user.id).execute()
                profile_exists = bool(profile_response.data)
                
                if not profile_exists:
                    missing_profiles.append({
                        "email": auth_user.email,
                        "user_id": auth_user.id,
                        "created_at": auth_user.created_at
                    })
            
            logger.info(f"📊 发现 {len(missing_profiles)} 个缺失的profile")
            
            # 创建缺失的profile
            created_count = 0
            for missing in missing_profiles:
                try:
                    profile_data = {
                        "id": missing["user_id"],
                        "nickname": missing["email"].split("@")[0],  # 使用邮箱前缀作为昵称
                        "created_at": missing["created_at"],
                        "updated_at": missing["created_at"]
                    }
                    
                    result = self.supabase.table('profiles').insert(profile_data).execute()
                    if result.data:
                        logger.info(f"✅ 创建profile成功: {missing['email']}")
                        created_count += 1
                    else:
                        logger.warning(f"⚠️ 创建profile失败: {missing['email']}")
                        
                except Exception as e:
                    logger.error(f"创建profile失败 {missing['email']}: {e}")
            
            logger.info(f"🎯 Profile创建完成！成功: {created_count}")
            
        except Exception as e:
            logger.error(f"创建缺失profile失败: {e}")

async def main():
    """主函数"""
    try:
        logger.info("🚀 启动重复注册修复工具...")
        
        fixer = DuplicateRegistrationFixer()
        
        # 修复重复注册
        await fixer.fix_all_duplicates()
        
        # 创建缺失的profile
        await fixer.create_missing_profiles()
        
        logger.info("🎉 所有修复操作完成！")
        
    except Exception as e:
        logger.error(f"❌ 修复过程出错: {e}")

if __name__ == "__main__":
    asyncio.run(main())
