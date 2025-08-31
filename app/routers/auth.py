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
        auth_service = AuthService()
        result = await auth_service.google_login()
        return result
    except ValueError as e:
        logger.error(f"Google登录配置错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Google登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google登录服务暂时不可用"
        )

@router.post("/google/callback")
async def google_callback(code: str = Form(...), state: str = Form(None)):
    """Google登录回调 - 处理授权码"""
    try:
        auth_service = AuthService()
        result = await auth_service.google_callback(code, state)
        return result
    except ValueError as e:
        logger.error(f"Google登录回调验证错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
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
        auth_service = AuthService()
        result = await auth_service.google_token_login(id_token)
        return result
    except ValueError as e:
        logger.error(f"Google ID Token验证错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Google ID Token登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google ID Token登录失败"
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
