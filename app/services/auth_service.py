from app.core.database import get_supabase, get_supabase_service
from app.core.config import settings
from app.models.user import UserCreate, UserLogin, UserResponse
from typing import Dict, Any, Optional
import logging
import uuid
import os
import httpx
import json
from datetime import datetime
from supabase import SupabaseException
from google.auth.transport import requests
from google.oauth2 import id_token
from urllib.parse import urlencode

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
    
    # 学习相关
    {"name": "Learning", "color": "#84CC16"},
    
    # 主题分类
    {"name": "Design", "color": "#BE185D"},
    
    # 工具和资源
    {"name": "Tool", "color": "#7C2D12"},
    
    # 项目相关
    {"name": "Project", "color": "#7C3AED"},
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
        """检查邮箱是否已存在（仅由 Supabase 自行校验，方法保持兼容但恒返回 False）"""
        try:
            return False
        except Exception:
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
            
            # 不再在注册前检查邮箱是否存在，交由 Supabase Auth 自行校验
            
            # 生成唯一用户名
            username = self._generate_unique_username(user.email)
            
            # 使用 Service Role 以管理员方式创建用户，避免邮件确认/网关导致的 500
            auth_response = self.supabase_service.auth.admin.create_user({
                "email": user.email,
                "password": user.password,
                "email_confirm": True,
                "user_metadata": {
                    "username": username,
                    "nickname": user.nickname
                }
            })
            
            # 检查注册结果
            if not hasattr(auth_response, 'user') or auth_response.user is None:
                self.logger.error("Supabase Auth注册失败: 用户对象为空")
                raise ValueError("用户创建失败")
            
            user_id = auth_response.user.id
            self.logger.info(f"✅ Supabase Auth用户创建成功: {user_id}")
            
            try:
                # 优先检查是否已有资料（避免与触发器重复插入）
                profile_exists = False
                try:
                    existing_profile = (
                        self.supabase_service
                        .table('profiles')
                        .select('id')
                        .eq('id', user_id)
                        .execute()
                    )
                    profile_exists = bool(existing_profile.data)
                except Exception as check_err:
                    self.logger.warning(f"检查现有资料失败，继续尝试创建: {check_err}")
                    profile_exists = False

                created_at_iso = datetime.utcnow().isoformat()

                if not profile_exists:
                    # 创建用户资料 - 使用正确的字段映射
                    profile_data = {
                        "id": user_id,  # 使用Supabase Auth生成的用户ID作为主键
                        "username": username,
                        "nickname": user.nickname,
                        "created_at": created_at_iso,
                        "updated_at": created_at_iso
                    }

                    profile_response = (
                        self.supabase_service
                        .table('profiles')
                        .insert(profile_data)
                        .execute()
                    )

                    if not profile_response.data:
                        # 如果profiles表创建失败，尝试删除已创建的auth用户
                        self.logger.error(f"❌ 用户资料创建失败，尝试回滚auth用户: {user.email}")
                        await self._rollback_auth_user(user_id)
                        raise ValueError("用户资料创建失败，请重试")
                    else:
                        self.logger.info(f"✅ 用户资料创建成功: {user.email}")
                else:
                    self.logger.info(f"ℹ️ 资料已存在，跳过创建: {user.email}")

                # 为新用户添加默认标签（若已存在则跳过）
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
                        "created_at": created_at_iso
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
            
            # 检查Google OAuth配置
            if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_REDIRECT_URI:
                self.logger.error("Google OAuth配置不完整")
                raise ValueError("Google OAuth配置不完整，请联系管理员")
            
            # 构建Google OAuth授权URL
            oauth_params = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "scope": "openid email profile",
                "response_type": "code",
                "access_type": "offline",
                "include_granted_scopes": "true",
                "state": str(uuid.uuid4())  # 防止CSRF攻击
            }
            
            oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(oauth_params)}"
            
            oauth_config = {
                "oauth_url": oauth_url,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "scope": "openid email profile",
                "response_type": "code",
                "state": oauth_params["state"]
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

    async def google_callback(self, code: str, state: str = None) -> dict:
        """Google登录回调处理"""
        try:
            self.logger.info("处理Google登录回调")
            
            # 检查必要配置
            if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET or not settings.GOOGLE_REDIRECT_URI:
                self.logger.error("Google OAuth配置不完整")
                raise ValueError("Google OAuth配置不完整")
            
            # 使用授权码交换访问令牌
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            }
            
            async with httpx.AsyncClient() as client:
                token_response = await client.post(token_url, data=token_data)
                
                if token_response.status_code != 200:
                    self.logger.error(f"获取访问令牌失败: {token_response.text}")
                    raise ValueError("获取访问令牌失败")
                
                token_data = token_response.json()
                access_token = token_data.get("access_token")
                id_token_str = token_data.get("id_token")
                
                if not access_token:
                    self.logger.error("未收到有效的访问令牌")
                    raise ValueError("未收到有效的访问令牌")
                
                # 使用访问令牌获取用户信息
                user_info_url = f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}"
                user_info_response = await client.get(user_info_url)
                
                if user_info_response.status_code != 200:
                    self.logger.error(f"获取用户信息失败: {user_info_response.text}")
                    raise ValueError("获取用户信息失败")
                
                user_info = user_info_response.json()
                self.logger.info(f"Google用户信息: {user_info.get('email')}")
                
                # 创建或登录用户
                return await self._handle_google_user(user_info, access_token)
            
        except Exception as e:
            self.logger.error(f"Google登录回调处理失败: {str(e)}")
            raise ValueError(f"Google登录回调处理失败: {str(e)}")

    async def google_token_login(self, id_token_str: str) -> dict:
        """使用Google ID Token登录 - 使用Supabase原生支持"""
        try:
            self.logger.info("用户使用Google ID Token登录")
            
            # 使用Supabase原生的sign_in_with_id_token方法
            auth_response = self.supabase.auth.sign_in_with_id_token(
                provider="google",
                token=id_token_str
            )
            
            if hasattr(auth_response, 'user') and auth_response.user:
                user = auth_response.user
                session = auth_response.session
                
                self.logger.info(f"✅ Google登录成功: {user.email}")
                
                # 确保用户有profile记录
                await self._ensure_user_profile(user)
                
                # 获取用户profile信息
                profile_query = self.supabase_service.table('profiles').select('*').eq('id', user.id).execute()
                profile_data = profile_query.data[0] if profile_query.data else {}
                
                return {
                    "success": True,
                    "message": "Google登录成功",
                    "data": {
                        "user": {
                            "id": user.id,
                            "email": user.email,
                            "username": profile_data.get('username', user.email.split('@')[0]),
                            "nickname": profile_data.get('nickname', user.user_metadata.get('name', ''))
                        },
                        "access_token": session.access_token if session else None,
                        "refresh_token": session.refresh_token if session else None,
                        "token_type": "bearer"
                    }
                }
            else:
                self.logger.error("Supabase Google登录失败: 无用户信息")
                raise ValueError("Google登录失败")
                
        except Exception as e:
            self.logger.error(f"Google ID Token登录失败: {str(e)}")
            raise ValueError(f"Google ID Token登录失败: {str(e)}")
    
    async def _ensure_user_profile(self, user) -> None:
        """确保用户有profile记录"""
        try:
            # 检查是否已有profile
            profile_query = self.supabase_service.table('profiles').select('id').eq('id', user.id).execute()
            
            if not profile_query.data:
                # 创建profile记录
                username = self._generate_unique_username(user.email)
                nickname = user.user_metadata.get('name', '') or user.user_metadata.get('given_name', '') or username
                
                profile_data = {
                    "id": user.id,
                    "username": username,
                    "nickname": nickname,
                    "avatar_url": user.user_metadata.get('picture', ''),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                self.supabase_service.table('profiles').insert(profile_data).execute()
                self.logger.info(f"✅ 为Google用户创建profile: {user.email}")
                
                # 添加默认标签
                await self.add_default_tags_for_user(user.id)
                
        except Exception as e:
            self.logger.error(f"确保用户profile失败: {str(e)}")
            # 不抛出错误，因为这不应该阻止登录
    
    async def _handle_google_user(self, user_info: dict, access_token: str = None) -> dict:
        """处理Google用户信息，创建或登录用户"""
        try:
            email = user_info.get('email')
            name = user_info.get('name', '')
            given_name = user_info.get('given_name', '')
            family_name = user_info.get('family_name', '')
            picture = user_info.get('picture', '')
            
            if not email:
                self.logger.error("Google用户信息中缺少邮箱")
                raise ValueError("Google用户信息中缺少邮箱")
            
            self.logger.info(f"处理Google用户: {email}")
            
            # 检查用户是否已存在（通过邮箱在auth.users表中查找）
            try:
                # 尝试通过邮箱查找用户（更高效的方法）
                existing_auth_user = None
                try:
                    # 尝试使用邮箱查找auth用户
                    auth_response = self.supabase_service.auth.admin.get_user_by_email(email)
                    if auth_response and hasattr(auth_response, 'user') and auth_response.user:
                        existing_auth_user = auth_response.user
                        self.logger.info(f"找到已存在的auth用户: {email}")
                except Exception as lookup_error:
                    # 如果直接查找失败，用户可能不存在
                    self.logger.info(f"Auth用户不存在: {email}")
                    existing_auth_user = None
                
                if existing_auth_user:
                    # 用户在auth中已存在，检查profiles表
                    user_id = existing_auth_user.id
                    profile_query = self.supabase_service.table('profiles').select('*').eq('id', user_id).execute()
                    
                    if profile_query.data:
                        # profiles表中也有记录，执行登录
                        user_data = profile_query.data[0]
                        self.logger.info(f"✅ Google用户登录成功: {email}")
                        
                        # 创建Supabase会话
                        auth_response = await self._create_supabase_session_for_user(user_data['id'])
                        
                        return {
                            "success": True,
                            "message": "Google登录成功",
                            "data": {
                                "user": {
                                    "id": user_data['id'],
                                    "email": email,
                                    "username": user_data['username'],
                                    "nickname": user_data['nickname']
                                },
                                "access_token": auth_response.get('access_token'),
                                "token_type": "bearer"
                            }
                        }
                    else:
                        # auth表有用户但profiles表没有，需要创建profile
                        self.logger.info(f"用户在auth表中存在但profiles表中缺失，创建profile: {email}")
                        return await self._create_profile_for_existing_auth_user(existing_auth_user, name, given_name, picture)
                else:
                    # 用户完全不存在，创建新用户
                    return await self._create_google_user(email, name, given_name, picture)
                    
            except Exception as e:
                self.logger.error(f"处理Google用户时出错: {str(e)}")
                raise ValueError(f"处理Google用户失败: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"处理Google用户失败: {str(e)}")
            raise ValueError(f"处理Google用户失败: {str(e)}")
    
    async def _create_google_user(self, email: str, name: str, given_name: str, picture: str = None) -> dict:
        """为Google用户创建新账户"""
        try:
            self.logger.info(f"为Google用户创建账户: {email}")
            
            # 生成唯一用户名
            username = self._generate_unique_username(email)
            nickname = given_name or name or username
            
            # 生成随机密码（用户不会使用，仅满足Supabase要求）
            temp_password = str(uuid.uuid4())
            
            # 创建Supabase Auth用户
            auth_response = self.supabase_service.auth.admin.create_user({
                "email": email,
                "password": temp_password,
                "email_confirm": True,
                "user_metadata": {
                    "username": username,
                    "nickname": nickname,
                    "provider": "google",
                    "picture": picture
                }
            })
            
            if not hasattr(auth_response, 'user') or auth_response.user is None:
                self.logger.error("创建Google用户失败: 用户对象为空")
                raise ValueError("用户创建失败")
            
            user_id = auth_response.user.id
            created_at_iso = datetime.utcnow().isoformat()
            
            # 创建用户资料
            profile_data = {
                "id": user_id,
                "username": username,
                "nickname": nickname,
                "avatar_url": picture,
                "created_at": created_at_iso,
                "updated_at": created_at_iso
            }
            
            profile_response = self.supabase_service.table('profiles').insert(profile_data).execute()
            
            if not profile_response.data:
                # 回滚auth用户
                await self._rollback_auth_user(user_id)
                raise ValueError("用户资料创建失败")
            
            # 添加默认标签
            await self.add_default_tags_for_user(user_id)
            
            # 创建会话
            session_response = await self._create_supabase_session_for_user(user_id)
            
            self.logger.info(f"🎉 Google用户创建成功: {email}")
            
            return {
                "success": True,
                "message": "Google账户创建成功",
                "data": {
                    "user": {
                        "id": user_id,
                        "email": email,
                        "username": username,
                        "nickname": nickname
                    },
                    "access_token": session_response.get('access_token'),
                    "token_type": "bearer"
                }
            }
            
        except Exception as e:
            self.logger.error(f"创建Google用户失败: {str(e)}")
            raise ValueError(f"创建Google用户失败: {str(e)}")
    
    async def _create_profile_for_existing_auth_user(self, auth_user, name: str, given_name: str, picture: str = None) -> dict:
        """为已存在的auth用户创建profile记录"""
        try:
            email = auth_user.email
            user_id = auth_user.id
            self.logger.info(f"为已存在的auth用户创建profile: {email}")
            
            # 生成唯一用户名
            username = self._generate_unique_username(email)
            nickname = given_name or name or username
            created_at_iso = datetime.utcnow().isoformat()
            
            # 创建用户资料
            profile_data = {
                "id": user_id,
                "username": username,
                "nickname": nickname,
                "avatar_url": picture,
                "created_at": created_at_iso,
                "updated_at": created_at_iso
            }
            
            profile_response = self.supabase_service.table('profiles').insert(profile_data).execute()
            
            if not profile_response.data:
                raise ValueError("创建用户资料失败")
            
            # 添加默认标签
            await self.add_default_tags_for_user(user_id)
            
            # 创建会话
            session_response = await self._create_supabase_session_for_user(user_id)
            
            self.logger.info(f"✅ 为已存在用户创建profile成功: {email}")
            
            return {
                "success": True,
                "message": "Google登录成功",
                "data": {
                    "user": {
                        "id": user_id,
                        "email": email,
                        "username": username,
                        "nickname": nickname
                    },
                    "access_token": session_response.get('access_token'),
                    "token_type": "bearer"
                }
            }
            
        except Exception as e:
            self.logger.error(f"为已存在auth用户创建profile失败: {str(e)}")
            raise ValueError(f"创建用户资料失败: {str(e)}")

    async def _create_supabase_session_for_user(self, user_id: str) -> dict:
        """为用户创建Supabase会话"""
        try:
            # 这里可以根据需要实现会话创建逻辑
            # 暂时返回空的访问令牌，实际应用中需要生成有效的JWT
            return {
                "access_token": f"google_auth_token_{user_id}_{uuid.uuid4()}",
                "token_type": "bearer"
            }
        except Exception as e:
            self.logger.error(f"创建用户会话失败: {str(e)}")
            return {"access_token": None}

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
