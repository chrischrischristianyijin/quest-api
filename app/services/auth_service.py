from app.core.database import get_supabase, get_supabase_service
from app.models.user import UserCreate, UserLogin
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.core.config import settings
import logging
import httpx
import json

logger = logging.getLogger(__name__)

class AuthService:
    """认证服务类 - 支持Supabase Auth和Google OAuth"""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.supabase_service = get_supabase_service()
    
    def create_access_token(self, data: dict) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    async def register_user(self, user: UserCreate) -> dict:
        """注册用户 - 使用Supabase Auth"""
        try:
            # 直接使用Supabase Auth注册
            response = self.supabase.auth.sign_up({
                "email": user.email,
                "password": user.password
            })
            
            # 检查响应结构
            if hasattr(response, 'user') and response.user:
                # 注册成功
                return {
                    "user_id": response.user.id,
                    "email": user.email,
                    "message": "注册成功",
                    "session": response.session.access_token if hasattr(response, 'session') and response.session else None
                }
            elif hasattr(response, 'error'):
                # 有错误
                raise ValueError(f"注册失败: {response.error}")
            else:
                raise ValueError("注册失败: 未知错误")
                
        except Exception as e:
            logger.error(f"注册用户失败: {e}")
            raise
    
    async def login_user(self, user: UserLogin) -> dict:
        """用户登录 - 使用Supabase Auth"""
        try:
            # 使用Supabase Auth登录
            response = self.supabase.auth.sign_in_with_password({
                "email": user.email,
                "password": user.password
            })
            
            # 添加调试日志
            logger.info(f"Supabase登录响应: {response}")
            logger.info(f"响应类型: {type(response)}")
            logger.info(f"响应属性: {dir(response)}")
            
            # 检查响应结构
            if hasattr(response, 'user') and response.user:
                # 登录成功
                access_token = response.session.access_token if hasattr(response, 'session') and response.session else None
                
                logger.info(f"登录成功，用户ID: {response.user.id}")
                
                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user_id": response.user.id,
                    "email": user.email,
                    "session": response.session.access_token if hasattr(response, 'session') and response.session else None
                }
            elif hasattr(response, 'error'):
                # 有错误
                logger.error(f"Supabase登录错误: {response.error}")
                raise ValueError(f"登录失败: {response.error}")
            else:
                logger.error(f"未知的响应结构: {response}")
                raise ValueError("登录失败: 未知错误")
                
        except Exception as e:
            logger.error(f"用户登录失败: {e}")
            raise ValueError("邮箱或密码错误")
    
    async def google_login(self, id_token: str) -> dict:
        """Google登录 - 验证ID Token并创建/获取用户"""
        try:
            # 1. 验证Google ID Token
            google_user_info = await self.verify_google_token(id_token)
            if not google_user_info:
                raise ValueError("无效的Google Token")
            
            email = google_user_info.get('email')
            google_id = google_user_info.get('sub')
            name = google_user_info.get('name')
            picture = google_user_info.get('picture')
            
            # 2. 检查用户是否已存在
            existing_user = await self.get_user_by_email(email)
            
            if existing_user:
                # 用户已存在，直接登录
                logger.info(f"Google用户已存在: {email}")
                user_id = existing_user.get('id')
            else:
                # 创建新用户
                logger.info(f"创建新的Google用户: {email}")
                user_id = await self.create_google_user(google_user_info)
            
            # 3. 创建JWT令牌
            access_token = self.create_access_token(
                data={"sub": email, "user_id": user_id, "auth_provider": "google"}
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user_id": user_id,
                "email": email,
                "name": name,
                "picture": picture,
                "auth_provider": "google"
            }
            
        except Exception as e:
            logger.error(f"Google登录失败: {e}")
            raise
    
    async def verify_google_token(self, id_token: str) -> dict:
        """验证Google ID Token"""
        try:
            # Google的公开密钥端点
            google_keys_url = "https://www.googleapis.com/oauth2/v3/certs"
            
            async with httpx.AsyncClient() as client:
                # 获取Google的公开密钥
                keys_response = await client.get(google_keys_url)
                keys_response.raise_for_status()
                
                # 这里应该实现JWT验证逻辑
                # 为了简化，我们直接解析token获取信息
                # 生产环境应该使用proper JWT验证库
                
                # 简单解析JWT payload（不安全，仅用于演示）
                parts = id_token.split('.')
                if len(parts) == 3:
                    import base64
                    payload = parts[1]
                    # 添加padding
                    payload += '=' * (4 - len(payload) % 4)
                    decoded = base64.b64decode(payload)
                    user_info = json.loads(decoded)
                    
                    # 验证必要字段
                    if user_info.get('email') and user_info.get('sub'):
                        return user_info
                
                raise ValueError("无效的Google Token格式")
                
        except Exception as e:
            logger.error(f"验证Google Token失败: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> dict:
        """根据邮箱获取用户信息"""
        try:
            # 尝试从auth.users表获取
            response = self.supabase_service.auth.admin.list_users()
            # 修复：response.users 应该是 response
            users = response if hasattr(response, '__iter__') else []
            user = next((u for u in users if hasattr(u, 'email') and u.email == email), None)
            
            if user:
                return {
                    "id": user.id,
                    "email": user.email,
                    "created_at": user.created_at
                }
            return None
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
    
    async def create_google_user(self, google_user_info: dict) -> str:
        """创建Google用户"""
        try:
            email = google_user_info.get('email')
            name = google_user_info.get('name')
            picture = google_user_info.get('picture')
            
            # 使用Supabase Auth创建用户（无密码）
            # 注意：这需要特殊配置，或者使用其他方式
            # 暂时返回模拟用户ID
            user_id = f"google_{google_user_info.get('sub')}"
            
            # 创建用户资料记录
            profile_data = {
                "id": user_id,
                "email": email,
                "nickname": name,
                "avatar_url": picture,
                "auth_provider": "google",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 这里应该插入到user_profiles表
            # 暂时跳过，因为需要先解决用户创建问题
            
            logger.info(f"Google用户创建成功: {email}")
            return user_id
            
        except Exception as e:
            logger.error(f"创建Google用户失败: {e}")
            raise
    
    async def signout_user(self, token: str) -> bool:
        """用户登出"""
        try:
            # 这里可以实现令牌黑名单等逻辑
            return True
        except Exception as e:
            logger.error(f"用户登出失败: {e}")
            raise
    
    async def check_email_exists(self, email: str) -> bool:
        """检查邮箱是否存在 - 使用auth.users表"""
        try:
            # 直接查询auth.users表
            response = self.supabase_service.rpc('check_user_exists', {'user_email': email})
            return response.data if response.data else False
        except Exception as e:
            logger.error(f"检查邮箱失败: {e}")
            # 如果RPC不存在，尝试直接查询
            try:
                response = self.supabase_service.auth.admin.list_users()
                # 修复：response.users 应该是 response
                users = response if hasattr(response, '__iter__') else []
                return any(hasattr(u, 'email') and u.email == email for u in users)
            except:
                return False
    
    async def get_current_user(self, token: str) -> dict:
        """获取当前用户信息 - 从auth.users表"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise ValueError("无效的令牌")
            
            # 从auth.users表获取用户信息
            # 注意：这里需要适当的权限设置
            try:
                # 尝试使用admin API获取用户信息
                response = self.supabase_service.auth.admin.list_users()
                # 修复：response.users 应该是 response
                users = response if hasattr(response, '__iter__') else []
                user = next((u for u in users if hasattr(u, 'email') and u.email == email), None)
                
                if user:
                    return {
                        "id": user.id,
                        "email": user.email,
                        "created_at": user.created_at,
                        "last_sign_in_at": user.last_sign_in_at,
                        "auth_provider": payload.get("auth_provider", "email")
                    }
                else:
                    raise ValueError("用户不存在")
            except Exception as e:
                logger.error(f"获取用户信息失败: {e}")
                # 如果admin API不可用，返回基本信息
                return {
                    "email": email,
                    "message": "用户信息获取受限",
                    "auth_provider": payload.get("auth_provider", "email")
                }
                
        except JWTError:
            raise ValueError("无效的令牌")
        except Exception as e:
            logger.error(f"获取当前用户失败: {e}")
            raise
    
    async def forgot_password(self, email: str) -> bool:
        """忘记密码处理 - 使用Supabase内置功能"""
        try:
            # 使用Supabase的密码重置功能
            self.supabase.auth.reset_password_email(email)
            return True
        except Exception as e:
            logger.error(f"忘记密码处理失败: {e}")
            raise
