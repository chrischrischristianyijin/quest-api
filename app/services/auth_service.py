from app.core.database import get_supabase, get_supabase_service
from app.models.user import UserCreate, UserLogin, UserResponse
from typing import Dict, Any, Optional
import logging
import uuid
import os
from datetime import datetime
from supabase import SupabaseException

# 配置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
        self.logger = logging.getLogger(__name__)

    def _generate_unique_username(self, email: str) -> str:
        """生成唯一用户名"""
        try:
            base_username = email.split('@')[0]
            # 清理用户名，只保留字母数字和下划线
            base_username = ''.join(c for c in base_username if c.isalnum() or c == '_')
            # 确保用户名不为空
            if not base_username:
                base_username = "user"
            
            # 生成唯一后缀
            unique_suffix = str(uuid.uuid4())[:8]
            username = f"{base_username}_{unique_suffix}"
            
            self.logger.info(f"生成用户名: {username} (基于邮箱: {email})")
            return username
            
        except Exception as e:
            self.logger.error(f"生成用户名失败: {e}")
            # 备用用户名生成
            return f"user_{str(uuid.uuid4())[:12]}"

    async def check_email_exists(self, email: str) -> bool:
        """检查邮箱是否已存在"""
        try:
            # 检查 auth.users 表
            auth_response = self.supabase_service.auth.admin.list_users()
            existing_emails = [user.email for user in auth_response.users if user.email == email]
            
            if existing_emails:
                self.logger.info(f"邮箱已存在于auth.users: {email}")
                return True
            
            # 检查 profiles 表
            profile_response = self.supabase_service.table('profiles').select('email').eq('email', email).execute()
            if profile_response.data:
                self.logger.info(f"邮箱已存在于profiles: {email}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"检查邮箱存在性时出错: {e}")
            # 如果检查失败，假设邮箱不存在，让注册流程继续
            return False

    async def add_default_tags_for_user(self, user_id: str):
        """为新用户添加默认标签"""
        try:
            self.logger.info(f"为用户 {user_id} 添加默认标签...")
            
            # 检查用户是否已有标签
            existing_tags = self.supabase_service.table('user_tags').select('name').eq('user_id', user_id).execute()
            existing_tag_names = [tag['name'] for tag in existing_tags.data] if existing_tags.data else []
            
            # 过滤掉已存在的标签
            new_tags = [tag for tag in DEFAULT_TAGS if tag['name'] not in existing_tag_names]
            
            if not new_tags:
                self.logger.info(f"用户 {user_id} 已有所有默认标签")
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
                    self.logger.info(f"✅ 添加标签: {tag['name']}")
                else:
                    self.logger.warning(f"⚠️ 添加标签失败: {tag['name']}")
            
            self.logger.info(f"🎉 为用户 {user_id} 添加了 {len(new_tags)} 个默认标签")
            
        except Exception as e:
            self.logger.error(f"为用户 {user_id} 添加默认标签时出错: {e}")

    async def register_user(self, user: UserCreate) -> dict:
        """用户注册"""
        try:
            self.logger.info(f"开始注册用户: {user.email}")
            
            # 检查邮箱是否已存在
            if await self.check_email_exists(user.email):
                raise ValueError("邮箱已被注册")
            
            # 生成唯一用户名
            username = self._generate_unique_username(user.email)
            
            # 使用Supabase Auth注册用户
            auth_response = self.supabase.auth.sign_up({
                "email": user.email,
                "password": user.password,
                "options": {
                    "data": {
                        "username": username,
                        "nickname": user.nickname,
                        # 可以添加其他元数据
                    }
                }
            })
            
            # 检查注册结果
            if not hasattr(auth_response, 'user') or auth_response.user is None:
                self.logger.error("Supabase Auth注册失败: 用户对象为空")
                raise ValueError("用户创建失败")
            
            user_id = auth_response.user.id
            self.logger.info(f"✅ Supabase Auth用户创建成功: {user_id}")
            
            try:
                # 创建用户资料 - 使用正确的字段映射
                profile_data = {
                    "id": user_id,  # 使用Supabase Auth生成的用户ID作为主键
                    "username": username,
                    "nickname": user.nickname,
                    "email": user.email,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                profile_response = self.supabase_service.table('profiles').insert(profile_data).execute()
                
                if profile_response.data:
                    self.logger.info(f"✅ 用户资料创建成功: {user.email}")
                    
                    # 为新用户添加默认标签
                    await self.add_default_tags_for_user(user_id)
                    
                    # 获取访问令牌
                    access_token = None
                    if hasattr(auth_response, 'session') and auth_response.session:
                        access_token = auth_response.session.access_token
                    
                    result_data = {
                        "user": {
                            "id": user_id,
                            "email": user.email,
                            "username": username,
                            "nickname": user.nickname,
                            "created_at": profile_data["created_at"]
                        },
                        "access_token": access_token,
                        "token_type": "bearer"
                    }
                    
                    self.logger.info(f"🎉 用户注册完成: {user.email}")
                    return {
                        "success": True,
                        "message": "用户注册成功",
                        "data": result_data
                    }
                else:
                    # 如果profiles表创建失败，尝试删除已创建的auth用户
                    self.logger.error(f"❌ 用户资料创建失败，尝试回滚auth用户: {user.email}")
                    await self._rollback_auth_user(user_id)
                    raise ValueError("用户资料创建失败，请重试")
                    
            except Exception as profile_error:
                # 如果profiles表操作失败，尝试删除已创建的auth用户
                self.logger.error(f"❌ 创建用户资料时出错: {profile_error}")
                await self._rollback_auth_user(user_id)
                raise ValueError(f"用户资料创建失败: {profile_error}")
                
        except SupabaseException as sube:
            # Supabase 特定异常处理
            self.logger.error(f"Supabase注册错误: {sube.message}")
            raise ValueError(f"注册失败: {sube.message}")
        except ValueError as ve:
            # 业务逻辑异常
            self.logger.error(f"注册验证失败: {ve}")
            raise ve
        except Exception as e:
            # 通用异常处理
            self.logger.error(f"注册未知错误: {str(e)}")
            raise ValueError(f"注册失败: {str(e)}")

    async def _rollback_auth_user(self, user_id: str):
        """回滚已创建的auth用户"""
        try:
            self.supabase_service.auth.admin.delete_user(user_id)
            self.logger.info(f"✅ 已回滚auth用户: {user_id}")
        except Exception as rollback_error:
            self.logger.error(f"⚠️ 回滚auth用户失败: {rollback_error}")

    async def login_user(self, user: UserLogin) -> dict:
        """用户登录"""
        try:
            self.logger.info(f"用户尝试登录: {user.email}")
            
            response = self.supabase.auth.sign_in_with_password({"email": user.email, "password": user.password})
            
            if hasattr(response, 'user') and response.user:
                access_token = response.session.access_token if hasattr(response, 'session') and response.session else None
                
                self.logger.info(f"✅ 用户登录成功: {user.email}")
                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user_id": response.user.id,
                    "email": user.email,
                    "session": access_token
                }
            elif hasattr(response, 'error'):
                self.logger.warning(f"⚠️ 登录失败 - 用户错误: {response.error}")
                raise ValueError(f"登录失败: {response.error}")
            else:
                self.logger.error(f"❌ 登录失败 - 未知错误: {user.email}")
                raise ValueError("登录失败: 未知错误")
                
        except SupabaseException as sube:
            self.logger.error(f"Supabase登录错误: {sube.message}")
            raise ValueError(f"登录失败: {sube.message}")
        except ValueError as ve:
            raise ve
        except Exception as e:
            self.logger.error(f"登录未知错误: {str(e)}")
            raise ValueError("邮箱或密码错误")

    async def signout_user(self, token: str) -> dict:
        """用户登出"""
        try:
            self.logger.info("用户尝试登出")
            
            response = self.supabase.auth.sign_out()
            
            self.logger.info("✅ 用户登出成功")
            return {"success": True, "message": "登出成功"}
            
        except SupabaseException as sube:
            self.logger.error(f"Supabase登出错误: {sube.message}")
            raise ValueError(f"登出失败: {sube.message}")
        except Exception as e:
            self.logger.error(f"登出未知错误: {str(e)}")
            raise ValueError("登出失败")

    async def get_current_user(self, token: str) -> dict:
        """获取当前用户信息"""
        try:
            self.logger.info("尝试获取当前用户信息")
            
            response = self.supabase.auth.get_user(token)
            
            if hasattr(response, 'user') and response.user:
                self.logger.info(f"✅ 获取用户信息成功: {response.user.email}")
                return {
                    "id": response.user.id,
                    "email": response.user.email
                }
            else:
                self.logger.warning("⚠️ 获取用户信息失败: 无效的令牌")
                raise ValueError("无效的令牌")
                
        except SupabaseException as sube:
            self.logger.error(f"Supabase获取用户信息错误: {sube.message}")
            raise ValueError(f"获取用户信息失败: {sube.message}")
        except Exception as e:
            self.logger.error(f"获取用户信息未知错误: {str(e)}")
            raise ValueError("无效的令牌")

    async def forgot_password(self, email: str) -> dict:
        """忘记密码"""
        try:
            self.logger.info(f"用户请求密码重置: {email}")
            
            response = self.supabase.auth.reset_password_email(email)
            
            self.logger.info(f"✅ 密码重置邮件发送成功: {email}")
            return {"success": True, "message": "密码重置邮件已发送"}
            
        except SupabaseException as sube:
            self.logger.error(f"Supabase密码重置错误: {sube.message}")
            raise ValueError(f"密码重置失败: {sube.message}")
        except Exception as e:
            self.logger.error(f"密码重置未知错误: {str(e)}")
            raise ValueError("发送密码重置邮件失败")

    async def google_login(self) -> dict:
        """Google登录入口"""
        try:
            self.logger.info("用户请求Google登录")
            
            # 这里应该返回Google OAuth的授权URL
            # 暂时返回占位符
            oauth_config = {
                "oauth_url": "https://accounts.google.com/oauth/authorize",
                "client_id": os.getenv('GOOGLE_CLIENT_ID', 'YOUR_GOOGLE_CLIENT_ID'),
                "redirect_uri": os.getenv('GOOGLE_REDIRECT_URI', 'YOUR_REDIRECT_URI'),
                "scope": "openid email profile",
                "response_type": "code"
            }
            
            self.logger.info("✅ Google登录配置获取成功")
            return {
                "success": True,
                "message": "Google登录",
                "data": oauth_config
            }
            
        except Exception as e:
            self.logger.error(f"Google登录配置获取失败: {str(e)}")
            raise ValueError("Google登录服务暂时不可用")

    async def google_callback(self, code: str) -> dict:
        """Google登录回调处理"""
        try:
            self.logger.info("处理Google登录回调")
            
            # 这里应该处理Google OAuth授权码
            # 暂时返回占位符
            self.logger.info(f"收到授权码: {code[:10]}...")
            
            return {
                "success": True,
                "message": "Google登录回调功能开发中",
                "data": {
                    "code": code,
                    "note": "需要实现授权码交换access_token的逻辑"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Google登录回调处理失败: {str(e)}")
            raise ValueError("Google登录回调处理失败")

    async def google_token_login(self, id_token: str) -> dict:
        """使用Google ID Token登录"""
        try:
            self.logger.info("用户使用Google ID Token登录")
            
            # 这里应该验证Google ID Token并创建或登录用户
            # 暂时返回占位符
            self.logger.info(f"收到ID Token: {id_token[:20]}...")
            
            return {
                "success": True,
                "message": "Google ID Token登录功能开发中",
                "data": {
                    "id_token": id_token,
                    "note": "需要实现ID Token验证和用户创建/登录逻辑"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Google ID Token登录失败: {str(e)}")
            raise ValueError("Google ID Token登录失败")

    async def check_email(self, email: str) -> dict:
        """检查邮箱是否可用"""
        try:
            self.logger.info(f"检查邮箱可用性: {email}")
            
            exists = await self.check_email_exists(email)
            
            if exists:
                self.logger.info(f"⚠️ 邮箱已被使用: {email}")
                return {
                    "available": False,
                    "message": "邮箱已被注册"
                }
            else:
                self.logger.info(f"✅ 邮箱可用: {email}")
                return {
                    "available": True,
                    "message": "邮箱可用"
                }
                
        except Exception as e:
            self.logger.error(f"检查邮箱可用性失败: {str(e)}")
            raise ValueError("检查邮箱可用性失败")
