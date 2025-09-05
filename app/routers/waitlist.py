from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.waitlist_service import WaitlistService
from app.models.waitlist import WaitlistCreate, WaitlistUpdate, WaitlistResponse
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["等待列表"])
security = HTTPBearer()

def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    # 检查X-Forwarded-For头（用于代理服务器）
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # 检查X-Real-IP头
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # 使用直接连接IP
    return request.client.host if request.client else "unknown"

@router.post("/join", response_model=Dict[str, Any])
async def join_waitlist(
    waitlist_data: WaitlistCreate,
    request: Request
):
    """加入等待列表"""
    try:
        waitlist_service = WaitlistService()
        
        # 获取客户端信息
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        
        result = await waitlist_service.add_to_waitlist(
            waitlist_data, 
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Successfully joined the waitlist! We'll notify you when Quest launches.",
                "data": {
                    "email": waitlist_data.email,
                    "status": "active"
                }
            }
        else:
            # 如果邮箱已存在且状态为active
            if "already exists" in result["message"]:
                return {
                    "success": True,
                    "message": "You're already on our waitlist! We'll notify you when Quest launches.",
                    "data": result["data"]
                }
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=result["message"]
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining waitlist: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to join waitlist. Please try again."
        )

@router.post("/unsubscribe", response_model=Dict[str, Any])
async def unsubscribe_waitlist(
    email: str,
    request: Request
):
    """退订等待列表"""
    try:
        waitlist_service = WaitlistService()
        
        result = await waitlist_service.unsubscribe_waitlist(email)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Successfully unsubscribed from waitlist"
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing from waitlist: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to unsubscribe. Please try again."
        )

@router.get("/stats", response_model=Dict[str, Any])
async def get_waitlist_stats(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取等待列表统计信息（需要认证）"""
    try:
        # 这里可以添加管理员权限检查
        # auth_service = AuthService()
        # current_user = await auth_service.get_current_user(credentials.credentials)
        # if not current_user.get("is_admin", False):
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        waitlist_service = WaitlistService()
        result = await waitlist_service.get_waitlist_stats()
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=500, 
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting waitlist stats: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to get waitlist stats"
        )

@router.get("/list", response_model=Dict[str, Any])
async def get_waitlist_list(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取等待列表条目列表（需要认证）"""
    try:
        # 这里可以添加管理员权限检查
        # auth_service = AuthService()
        # current_user = await auth_service.get_current_user(credentials.credentials)
        # if not current_user.get("is_admin", False):
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        waitlist_service = WaitlistService()
        result = await waitlist_service.get_all_waitlist(
            page=page, 
            limit=limit, 
            status=status
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=500, 
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting waitlist list: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to get waitlist list"
        )

@router.put("/{waitlist_id}/status", response_model=Dict[str, Any])
async def update_waitlist_status(
    waitlist_id: str,
    update_data: WaitlistUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """更新等待列表条目状态（需要认证）"""
    try:
        # 这里可以添加管理员权限检查
        # auth_service = AuthService()
        # current_user = await auth_service.get_current_user(credentials.credentials)
        # if not current_user.get("is_admin", False):
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        waitlist_service = WaitlistService()
        result = await waitlist_service.update_waitlist(waitlist_id, update_data)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=404, 
                detail=result["message"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating waitlist status: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to update waitlist status"
        )
