from fastapi import APIRouter, HTTPException, Depends, status, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.user import UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService
from app.core.database import get_supabase
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["认证"])
security = HTTPBearer()

@router.post("/register", response_model=Dict[str, Any])
async def register(user: UserCreate):
    """用户注册"""
    try:
        auth_service = AuthService()
        result = await auth_service.register_user(user)
        return {
            "success": True,
            "message": "注册成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"注册失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/signup", response_model=Dict[str, Any])
async def signup(user: UserCreate):
    """用户注册 - signup别名"""
    return await register(user)

@router.post("/login", response_model=Dict[str, Any])
async def login(user: UserLogin):
    """用户登录"""
    try:
        auth_service = AuthService()
        result = await auth_service.login_user(user)
        return {
            "success": True,
            "message": "登录成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

@router.get("/google/login")
async def google_login():
    """Google登录端点 - 返回OAuth URL"""
    try:
        # 这里应该返回Google OAuth URL
        # 暂时返回占位符
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google登录服务暂时不可用"
        )

@router.post("/google/callback")
async def google_callback(code: str = Form(...)):
    """Google登录回调 - 处理授权码"""
    try:
        # 这里应该处理Google OAuth授权码
        # 暂时返回占位符
        return {
            "success": True,
            "message": "Google登录回调功能开发中",
            "data": {
                "code": code,
                "note": "需要实现授权码交换access_token的逻辑"
            }
        }
    except Exception as e:
        logger.error(f"Google登录回调失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google登录回调处理失败"
        )

@router.post("/google/token")
async def google_token_login(id_token: str = Form(...)):
    """Google ID Token登录"""
    try:
        # 这里应该验证Google ID Token
        # 暂时返回占位符
        return {
            "success": True,
            "message": "Google ID Token登录功能开发中",
            "data": {
                "id_token": id_token,
                "note": "需要实现Google ID Token验证逻辑"
            }
        }
    except Exception as e:
        logger.error(f"Google ID Token登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google ID Token登录处理失败"
        )

@router.post("/cleanup-duplicate")
async def cleanup_duplicate_registration(email: str = Form(...)):
    """清理重复注册（管理员功能）"""
    try:
        auth_service = AuthService()
        duplicate_check = await auth_service.check_duplicate_registration(email)
        
        if duplicate_check["is_duplicate"]:
            # 清理重复注册
            if duplicate_check["user_id"]:
                auth_service.supabase_service.auth.admin.delete_user(duplicate_check["user_id"])
                logger.info(f"✅ 已清理重复注册: {email}")
                
                return {
                    "success": True,
                    "message": "重复注册清理成功",
                    "data": {
                        "email": email,
                        "cleaned_user_id": duplicate_check["user_id"],
                        "note": "现在可以重新注册了"
                    }
                }
        else:
            return {
                "success": False,
                "message": "未检测到重复注册",
                "data": duplicate_check
            }
            
    except Exception as e:
        logger.error(f"清理重复注册失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理重复注册失败: {str(e)}"
        )

@router.post("/signout")
async def signout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """用户登出"""
    try:
        auth_service = AuthService()
        await auth_service.signout_user(credentials.credentials)
        return {
            "success": True,
            "message": "登出成功"
        }
    except Exception as e:
        logger.error(f"登出失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/check-email")
async def check_email(email: str):
    """检查邮箱是否存在"""
    try:
        auth_service = AuthService()
        exists = await auth_service.check_email_exists(email)
        return {
            "success": True,
            "data": {"exists": exists}
        }
    except Exception as e:
        logger.error(f"检查邮箱失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/profile", response_model=Dict[str, Any])
async def get_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户信息"""
    try:
        auth_service = AuthService()
        user = await auth_service.get_current_user(credentials.credentials)
        return {
            "success": True,
            "data": user
        }
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="获取用户信息失败"
        )

@router.post("/forgot-password")
async def forgot_password(email: str):
    """忘记密码"""
    try:
        auth_service = AuthService()
        await auth_service.forgot_password(email)
        return {
            "success": True,
            "message": "重置密码邮件已发送"
        }
    except Exception as e:
        logger.error(f"忘记密码处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
