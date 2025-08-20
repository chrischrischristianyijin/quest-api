from app.core.database import get_supabase, get_supabase_service
from app.models.user import UserCreate, UserLogin
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """认证服务类"""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.supabase_service = get_supabase_service()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    async def register_user(self, user: UserCreate) -> dict:
        """注册用户"""
        try:
            # 检查邮箱是否已存在
            if await self.check_email_exists(user.email):
                raise ValueError("邮箱已存在")
            
            # 创建用户 - 使用Supabase Auth
            response = self.supabase.auth.sign_up({
                "email": user.email,
                "password": user.password
            })
            
            if response.user:
                # 在users表中创建用户记录
                user_data = {
                    "id": response.user.id,
                    "email": user.email,
                    "nickname": user.nickname,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                self.supabase_service.table("users").insert(user_data).execute()
                
                return {
                    "user_id": response.user.id,
                    "email": user.email,
                    "message": "注册成功"
                }
            else:
                raise ValueError("注册失败")
                
        except Exception as e:
            logger.error(f"注册用户失败: {e}")
            raise
    
    async def login_user(self, user: UserLogin) -> dict:
        """用户登录"""
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": user.email,
                "password": user.password
            })
            
            if response.user:
                # 创建JWT令牌
                access_token = self.create_access_token(
                    data={"sub": user.email, "user_id": response.user.id}
                )
                
                return {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user_id": response.user.id,
                    "email": user.email
                }
            else:
                raise ValueError("登录失败")
                
        except Exception as e:
            logger.error(f"用户登录失败: {e}")
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
        """检查邮箱是否存在"""
        try:
            response = self.supabase_service.table("users").select("id").eq("email", email).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"检查邮箱失败: {e}")
            return False
    
    async def get_current_user(self, token: str) -> dict:
        """获取当前用户信息"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise ValueError("无效的令牌")
            
            # 从数据库获取用户信息
            response = self.supabase_service.table("users").select("*").eq("email", email).execute()
            if response.data:
                return response.data[0]
            else:
                raise ValueError("用户不存在")
                
        except JWTError:
            raise ValueError("无效的令牌")
        except Exception as e:
            logger.error(f"获取当前用户失败: {e}")
            raise
    
    async def forgot_password(self, email: str) -> bool:
        """忘记密码处理"""
        try:
            # 这里可以实现发送重置密码邮件的逻辑
            return True
        except Exception as e:
            logger.error(f"忘记密码处理失败: {e}")
            raise
