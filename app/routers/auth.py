from fastapi import APIRouter, HTTPException, Depends, status, Form, Request
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

@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(refresh_token: str = Form(...)):
    """刷新访问令牌"""
    try:
        auth_service = AuthService()
        result = await auth_service.refresh_token(refresh_token)
        return {
            "success": True,
            "message": "令牌刷新成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"令牌刷新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌刷新失败，请重新登录"
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

@router.get("/token-status", response_model=Dict[str, Any])
async def check_token_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """检查token状态和剩余时间"""
    try:
        token = credentials.credentials
        auth_service = AuthService()
        
        # 基本信息
        token_info = {
            "token_length": len(token),
            "token_prefix": token[:20] + "..." if len(token) > 20 else token,
            "is_google_token": any(token.startswith(prefix) for prefix in [
                "google_existing_user_", "google_new_user_", "google_auth_token_"
            ]),
            "is_jwt_format": token.count('.') == 2
        }
        
        # 检查JWT过期时间
        if token_info["is_jwt_format"]:
            try:
                import base64
                import json
                import time
                
                payload_part = token.split('.')[1]
                missing_padding = len(payload_part) % 4
                if missing_padding:
                    payload_part += '=' * (4 - missing_padding)
                
                payload_data = json.loads(base64.urlsafe_b64decode(payload_part))
                exp_timestamp = payload_data.get('exp')
                
                if exp_timestamp:
                    current_time = int(time.time())
                    exp_time = int(exp_timestamp)
                    time_remaining = exp_time - current_time
                    
                    token_info.update({
                        "expires_at": exp_time,
                        "expires_at_readable": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp_time)),
                        "time_remaining": time_remaining,
                        "is_expired": time_remaining <= 0,
                        "hours_remaining": time_remaining // 3600 if time_remaining > 0 else 0,
                        "minutes_remaining": (time_remaining % 3600) // 60 if time_remaining > 0 else 0
                    })
                else:
                    token_info["expires_at"] = None
                    token_info["is_expired"] = False
                    
            except Exception as e:
                token_info["expiry_error"] = str(e)
        
        # 尝试验证
        try:
            user = await auth_service.get_current_user(token)
            token_info["validation_status"] = "success"
            token_info["user_id"] = user.get("id")
            token_info["user_email"] = user.get("email")
        except Exception as validation_error:
            token_info["validation_status"] = "failed"
            token_info["error"] = str(validation_error)
        
        return {
            "success": True,
            "data": token_info
        }
    except Exception as e:
        logger.error(f"Token状态检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token状态检查失败: {str(e)}"
        )

@router.post("/debug-token", response_model=Dict[str, Any])
async def debug_token(request: Request):
    """调试Token验证 - 返回详细的验证信息"""
    try:
        auth_service = AuthService()
        
        # 从请求头中提取token
        authorization_header = request.headers.get("authorization", "")
        
        token_info = {
            "raw_header": authorization_header[:50] + "..." if len(authorization_header) > 50 else authorization_header,
            "header_length": len(authorization_header),
            "has_authorization_header": bool(authorization_header)
        }
        
        if not authorization_header:
            token_info["validation_status"] = "failed"
            token_info["error"] = "缺少Authorization header"
            return {
                "success": False,
                "data": token_info
            }
        
        try:
            # 使用统一的token提取方法
            token = auth_service._extract_token_from_header(authorization_header)
            
            # 基本信息
            token_info.update({
                "token_length": len(token),
                "token_prefix": token[:20] + "..." if len(token) > 20 else token,
                "is_google_token": any(token.startswith(prefix) for prefix in [
                    "google_existing_user_", "google_new_user_", "google_auth_token_"
                ]),
                "is_jwt_format": token.count('.') == 2
            })
            
            # 尝试验证
            user = await auth_service.get_current_user(token)
            token_info["validation_status"] = "success"
            token_info["user_id"] = user.get("id")
            token_info["user_email"] = user.get("email")
            
        except Exception as validation_error:
            token_info["validation_status"] = "failed"
            token_info["error"] = str(validation_error)
        
        return {
            "success": True,
            "data": token_info
        }
    except Exception as e:
        logger.error(f"Token调试失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token调试失败: {str(e)}"
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
