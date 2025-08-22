from app.core.database import get_supabase, get_supabase_service
from app.models.user import UserCreate, UserLogin, UserResponse
from typing import Dict, Any, Optional
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# 默认标签配置
DEFAULT_TAGS = [
    # 技术相关
    {"name": "Technology", "color": "#3B82F6"},
    {"name": "Programming", "color": "#10B981"},
    {"name": "AI", "color": "#8B5CF6"},
    {"name": "Web Development", "color": "#EF4444"},
    
    # 学习相关
    {"name": "Learning", "color": "#84CC16"},
    {"name": "Tutorial", "color": "#F97316"},
    
    # 内容类型
    {"name": "Article", "color": "#059669"},
    {"name": "Video", "color": "#DC2626"},
    
    # 主题分类
    {"name": "Business", "color": "#1F2937"},
    {"name": "Productivity", "color": "#047857"},
    {"name": "Design", "color": "#BE185D"},
    
    # 工具和资源
    {"name": "Tool", "color": "#7C2D12"},
    {"name": "Resource", "color": "#1E40AF"},
    
    # 项目相关
    {"name": "Project", "color": "#7C3AED"},
    {"name": "Ideas", "color": "#F59E0B"}
]

class AuthService:
    def __init__(self):
        self.supabase = get_supabase()
        self.supabase_service = get_supabase_service()

    async def add_default_tags_for_user(self, user_id: str):
        """为新用户添加默认标签"""
        try:
            logger.info(f"为用户 {user_id} 添加默认标签...")
            
            # 检查用户是否已有标签
            existing_tags = self.supabase_service.table('user_tags').select('name').eq('user_id', user_id).execute()
            existing_tag_names = [tag['name'] for tag in existing_tags.data] if existing_tags.data else []
            
            # 过滤掉已存在的标签
            new_tags = [tag for tag in DEFAULT_TAGS if tag['name'] not in existing_tag_names]
            
            if not new_tags:
                logger.info(f"用户 {user_id} 已有所有默认标签")
                return
            
            # 批量插入新标签
            for tag in new_tags:
                tag_data = {
                    "user_id": user_id,
                    "name": tag["name"],
                    "color": tag["color"]
                }
                
                result = self.supabase_service.table('user_tags').insert(tag_data).execute()
                if result.data:
                    logger.info(f"✅ 添加标签: {tag['name']}")
                else:
                    logger.warning(f"⚠️ 添加标签失败: {tag['name']}")
            
            logger.info(f"🎉 为用户 {user_id} 添加了 {len(new_tags)} 个默认标签")
            
        except Exception as e:
            logger.error(f"为用户 {user_id} 添加默认标签时出错: {e}")

    async def register_user(self, user: UserCreate) -> dict:
        """用户注册"""
        try:
            # 检查邮箱是否已存在
            if await self.check_email_exists(user.email):
                raise ValueError("邮箱已被注册")
            
            # 检查是否存在重复注册情况
            duplicate_check = await self.check_duplicate_registration(user.email)
            if duplicate_check["is_duplicate"]:
                logger.warning(f"⚠️ 检测到重复注册: {user.email}, user_id: {duplicate_check['user_id']}")
                
                # 尝试清理重复注册：删除auth用户，重新开始
                try:
                    if duplicate_check["user_id"]:
                        self.supabase_service.auth.admin.delete_user(duplicate_check["user_id"])
                        logger.info(f"✅ 已清理重复注册的auth用户: {user.email}")
                except Exception as cleanup_error:
                    logger.error(f"⚠️ 清理重复注册失败: {cleanup_error}")
                    raise ValueError("检测到重复注册，请稍后重试或联系客服")
            
            # 使用Supabase Auth注册用户
            response = self.supabase.auth.sign_up({
                "email": user.email,
                "password": user.password
            })
            
            if hasattr(response, 'user') and response.user:
                user_id = response.user.id
                
                try:
                    # 创建用户资料
                    profile_data = {
                        "id": user_id,
                        "nickname": user.nickname,
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    profile_response = self.supabase_service.table('profiles').insert(profile_data).execute()
                    
                    if profile_response.data:
                        logger.info(f"✅ 用户资料创建成功: {user.email}")
                        
                        # 为新用户添加默认标签
                        await self.add_default_tags_for_user(user_id)
                        
                        # 获取访问令牌
                        access_token = response.session.access_token if hasattr(response, 'session') and response.session else None
                        
                        return {
                            "success": True,
                            "message": "用户注册成功",
                            "data": {
                                "user": {
                                    "id": user_id,
                                    "email": user.email,
                                    "nickname": user.nickname,
                                    "created_at": profile_data["created_at"]
                                },
                                "access_token": access_token,
                                "token_type": "bearer"
                            }
                        }
                    else:
                        # 如果profiles表创建失败，尝试删除已创建的auth用户
                        logger.error(f"❌ 用户资料创建失败，尝试回滚auth用户: {user.email}")
                        try:
                            self.supabase_service.auth.admin.delete_user(user_id)
                            logger.info(f"✅ 已回滚auth用户: {user.email}")
                        except Exception as rollback_error:
                            logger.error(f"⚠️ 回滚auth用户失败: {rollback_error}")
                        
                        raise ValueError("用户资料创建失败，请重试")
                        
                except Exception as profile_error:
                    # 如果profiles表操作失败，尝试删除已创建的auth用户
                    logger.error(f"❌ 创建用户资料时出错: {profile_error}")
                    try:
                        self.supabase_service.auth.admin.delete_user(user_id)
                        logger.info(f"✅ 已回滚auth用户: {user.email}")
                    except Exception as rollback_error:
                        logger.error(f"⚠️ 回滚auth用户失败: {rollback_error}")
                    
                    raise ValueError(f"用户资料创建失败: {profile_error}")
                    
            elif hasattr(response, 'error'):
                raise ValueError(f"注册失败: {response.error}")
            else:
                raise ValueError("注册失败: 未知错误")
                
        except Exception as e:
            logger.error(f"用户注册失败: {e}")
            raise ValueError(f"注册失败: {e}")

    async def login_user(self, user: UserLogin) -> dict:
        """用户登录"""
        try:
            response = self.supabase.auth.sign_in_with_password({"email": user.email, "password": user.password})
            if hasattr(response, 'user') and response.user:
                access_token = response.session.access_token if hasattr(response, 'session') and response.session else None
                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user_id": response.user.id,
                    "email": user.email,
                    "session": access_token
                }
            elif hasattr(response, 'error'):
                raise ValueError(f"登录失败: {response.error}")
            else:
                raise ValueError("登录失败: 未知错误")
        except Exception as e:
            logger.error(f"用户登录失败: {e}")
            raise ValueError("邮箱或密码错误")

    async def signout_user(self, token: str) -> dict:
        """用户登出"""
        try:
            response = self.supabase.auth.sign_out()
            return {"success": True, "message": "登出成功"}
        except Exception as e:
            logger.error(f"用户登出失败: {e}")
            raise ValueError("登出失败")

    async def check_email_exists(self, email: str) -> bool:
        """检查邮箱是否已存在"""
        try:
            response = self.supabase_service.auth.admin.list_users()
            for user in response.users:
                if user.email == email:
                    return True
            return False
        except Exception as e:
            logger.error(f"检查邮箱失败: {e}")
            return False

    async def check_duplicate_registration(self, email: str) -> dict:
        """检查是否存在重复注册情况"""
        try:
            # 检查auth.users表
            auth_users = self.supabase_service.auth.admin.list_users()
            auth_user = None
            for user in auth_users.users:
                if user.email == email:
                    auth_user = user
                    break
            
            # 检查profiles表
            profile_exists = False
            if auth_user:
                profile_response = self.supabase_service.table('profiles').select('id').eq('id', auth_user.id).execute()
                profile_exists = bool(profile_response.data)
            
            return {
                "email": email,
                "auth_user_exists": bool(auth_user),
                "profile_exists": profile_exists,
                "user_id": auth_user.id if auth_user else None,
                "is_duplicate": auth_user and not profile_exists  # 只有auth存在但profile不存在才是重复注册
            }
        except Exception as e:
            logger.error(f"检查重复注册失败: {e}")
            return {
                "email": email,
                "auth_user_exists": False,
                "profile_exists": False,
                "user_id": None,
                "is_duplicate": False,
                "error": str(e)
            }

    async def get_current_user(self, token: str) -> dict:
        """获取当前用户信息"""
        try:
            response = self.supabase.auth.get_user(token)
            if hasattr(response, 'user') and response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email
                }
            else:
                raise ValueError("无效的令牌")
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            raise ValueError("无效的令牌")

    async def forgot_password(self, email: str) -> dict:
        """忘记密码"""
        try:
            response = self.supabase.auth.reset_password_email(email)
            return {"success": True, "message": "密码重置邮件已发送"}
        except Exception as e:
            logger.error(f"发送密码重置邮件失败: {e}")
            raise ValueError("发送密码重置邮件失败")

    async def google_login(self) -> dict:
        """Google登录入口"""
        try:
            # 这里应该返回Google OAuth的授权URL
            return {
                "success": True,
                "message": "Google登录",
                "data": {
                    "oauth_url": "https://accounts.google.com/oauth/authorize",
                    "client_id": "YOUR_GOOGLE_CLIENT_ID",
                    "redirect_uri": "YOUR_REDIRECT_URI",
                    "scope": "openid email profile",
                    "response_type": "code"
                }
            }
        except Exception as e:
            logger.error(f"Google登录失败: {e}")
            raise ValueError("Google登录失败")

    async def verify_google_token(self, id_token: str) -> dict:
        """验证Google ID Token"""
        try:
            # 这里应该实现Google ID Token的验证逻辑
            return {
                "success": True,
                "message": "Google登录成功",
                "data": {
                    "access_token": "mock_token",
                    "token_type": "bearer",
                    "user_id": "mock_user_id",
                    "email": "user@gmail.com",
                    "auth_provider": "google"
                }
            }
        except Exception as e:
            logger.error(f"Google Token验证失败: {e}")
            raise ValueError("Google Token验证失败")

    async def create_google_user(self, google_user_data: dict) -> dict:
        """创建Google用户"""
        try:
            # 这里应该实现Google用户的创建逻辑
            return {
                "success": True,
                "message": "Google用户创建成功",
                "data": google_user_data
            }
        except Exception as e:
            logger.error(f"创建Google用户失败: {e}")
            raise ValueError("创建Google用户失败")
