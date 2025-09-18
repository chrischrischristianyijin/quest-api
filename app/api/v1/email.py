"""
Email API endpoints for digest system.
Handles preview, preferences, unsubscribe, and cron operations.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import os
import hmac
import hashlib

from ...services.digest_repo import DigestRepo
from ...services.digest_job import DigestJob, DigestJobConfig
from ...services.digest_content import DigestContentGenerator
from ...services.digest_time import get_week_boundaries
from ...services.email_sender import email_sender

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])

# Pydantic models
class EmailPreferencesUpdate(BaseModel):
    weekly_digest_enabled: Optional[bool] = None
    preferred_day: Optional[int] = Field(None, ge=0, le=6)
    preferred_hour: Optional[int] = Field(None, ge=0, le=23)
    timezone: Optional[str] = None
    no_activity_policy: Optional[str] = Field(None, pattern="^(skip|brief|suggestions)$")

class DigestPreviewRequest(BaseModel):
    user_id: str
    week_start: Optional[str] = None

class UnsubscribeRequest(BaseModel):
    token: str

# Dependency to get current user
async def get_current_user_id(request: Request) -> str:
    """Get current user ID from JWT token in Authorization header."""
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    try:
        from jose import JWTError, jwt
    except ImportError:
        # Fallback if jose is not available
        import jwt as pyjwt
        JWTError = pyjwt.InvalidTokenError
    import os
    from ...core.config import settings
    
    # Get the Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = auth_header.split(" ")[1]
    
    try:
        # Decode JWT token with proper verification
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub") or payload.get("user_id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# Dependency to verify cron secret
def verify_cron_secret(request: Request) -> bool:
    """Verify cron job secret for security."""
    secret = os.getenv("CRON_SECRET")
    if not secret:
        return True  # No secret configured
    
    provided_secret = request.headers.get("X-Cron-Secret")
    if not provided_secret:
        raise HTTPException(status_code=401, detail="Cron secret required")
    
    if not hmac.compare_digest(secret, provided_secret):
        raise HTTPException(status_code=403, detail="Invalid cron secret")
    
    return True

@router.get("/preferences")
async def get_email_preferences(
    user_id: str = Depends(get_current_user_id),
    repo: DigestRepo = Depends()
):
    """Get user's email preferences."""
    try:
        preferences = await repo.get_user_email_preferences(user_id)
        if not preferences:
            # Create default preferences for new user
            success = await repo.create_default_email_preferences(user_id)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create default preferences")
            
            # Get the newly created preferences
            preferences = await repo.get_user_email_preferences(user_id)
            if not preferences:
                raise HTTPException(status_code=500, detail="Failed to retrieve preferences after creation")
        
        return {
            "success": True,
            "preferences": {
                "weekly_digest_enabled": preferences["weekly_digest_enabled"],
                "preferred_day": preferences["preferred_day"],
                "preferred_hour": preferences["preferred_hour"],
                "timezone": preferences["timezone"],
                "no_activity_policy": preferences["no_activity_policy"]
            }
        }
    except Exception as e:
        logger.error(f"Error getting email preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to get email preferences")

@router.put("/preferences")
async def update_email_preferences(
    preferences: EmailPreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
    repo: DigestRepo = Depends()
):
    """Update user's email preferences."""
    try:
        # Convert to dict and remove None values
        prefs_dict = preferences.dict(exclude_unset=True)
        
        success = await repo.update_user_email_preferences(user_id, prefs_dict)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update preferences")
        
        return {
            "success": True,
            "message": "Email preferences updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating email preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to update email preferences")

@router.post("/digest/preview")
async def preview_digest(
    request: DigestPreviewRequest,
    user_id: str = Depends(get_current_user_id),
    repo: DigestRepo = Depends()
):
    """Preview the next digest for a user."""
    try:
        # Get user data
        user_prefs = await repo.get_user_email_preferences(user_id)
        if not user_prefs:
            raise HTTPException(status_code=404, detail="User preferences not found")
        
        # Get user basic info (you might need to fetch this from your users table)
        user_data = {
            "id": user_id,
            "email": "user@example.com",  # You'll need to fetch this
            "first_name": "User",  # You'll need to fetch this
            "timezone": user_prefs["timezone"]
        }
        
        # Determine week boundaries
        if request.week_start:
            week_start = datetime.fromisoformat(request.week_start).date()
        else:
            now_utc = datetime.now(timezone.utc)
            week_boundaries = get_week_boundaries(now_utc, user_prefs["timezone"])
            week_start = week_boundaries["prev_week_start"].date()
        
        # Get user activity for the week
        start_utc = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_utc = start_utc.replace(hour=23, minute=59, second=59) + timedelta(days=6)
        
        insights, stacks = await repo.get_user_activity(user_id, start_utc, end_utc)
        
        # Generate content
        content_generator = DigestContentGenerator()
        payload = content_generator.build_user_digest_payload(
            user_data, insights, stacks, user_prefs["no_activity_policy"]
        )
        
        # Render email content
        from ...services.digest_job import DigestJob
        job = DigestJob(repo)
        render_result = await job._render_email_content(payload)
        
        if not render_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to render email content")
        
        return {
            "success": True,
            "preview": {
                "subject": render_result["subject"],
                "html_content": render_result["html_content"],
                "text_content": render_result["text_content"],
                "payload": payload
            }
        }
    except Exception as e:
        logger.error(f"Error generating digest preview: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate preview")

@router.get("/digest/preview", response_class=HTMLResponse)
async def preview_digest_html(
    user_id: str = Depends(get_current_user_id),
    repo: DigestRepo = Depends()
):
    """Preview the next digest as HTML."""
    try:
        # Generate preview data
        request = DigestPreviewRequest(user_id=user_id)
        preview_data = await preview_digest(request, user_id, repo)
        
        if not preview_data["success"]:
            raise HTTPException(status_code=500, detail="Failed to generate preview")
        
        # Return HTML content
        return HTMLResponse(content=preview_data["preview"]["html_content"])
    except Exception as e:
        logger.error(f"Error generating HTML preview: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate HTML preview")

@router.post("/unsubscribe")
async def unsubscribe_user(
    request: UnsubscribeRequest,
    repo: DigestRepo = Depends()
):
    """Unsubscribe a user from digest emails."""
    try:
        # Get user by token
        user = await repo.get_user_by_unsubscribe_token(request.token)
        if not user:
            raise HTTPException(status_code=404, detail="Invalid unsubscribe token")
        
        # Disable digest
        success = await repo.disable_user_digest(user["id"])
        if not success:
            raise HTTPException(status_code=500, detail="Failed to unsubscribe")
        
        return {
            "success": True,
            "message": f"Successfully unsubscribed {user['email']} from digest emails"
        }
    except Exception as e:
        logger.error(f"Error unsubscribing user: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsubscribe")

@router.get("/unsubscribe/{token}")
async def unsubscribe_user_get(
    token: str,
    repo: DigestRepo = Depends()
):
    """Unsubscribe a user via GET request (for email links)."""
    try:
        # Get user by token
        user = await repo.get_user_by_unsubscribe_token(token)
        if not user:
            return HTMLResponse(
                content="<html><body><h1>Invalid unsubscribe link</h1><p>The unsubscribe link is invalid or has expired.</p></body></html>",
                status_code=404
            )
        
        # Disable digest
        success = await repo.disable_user_digest(user["id"])
        if not success:
            return HTMLResponse(
                content="<html><body><h1>Unsubscribe failed</h1><p>There was an error processing your unsubscribe request. Please try again later.</p></body></html>",
                status_code=500
            )
        
        return HTMLResponse(
            content=f"<html><body><h1>Successfully unsubscribed</h1><p>You have been unsubscribed from Quest digest emails. We're sorry to see you go!</p><p>You can resubscribe anytime in your <a href='https://quest.example.com/settings'>email preferences</a>.</p></body></html>"
        )
    except Exception as e:
        logger.error(f"Error processing unsubscribe: {e}")
        return HTMLResponse(
            content="<html><body><h1>Error</h1><p>There was an error processing your request. Please try again later.</p></body></html>",
            status_code=500
        )

@router.post("/cron/digest")
async def run_digest_cron(
    background_tasks: BackgroundTasks,
    request: Request,
    _: bool = Depends(verify_cron_secret)
):
    """Run the digest cron job (called by scheduler)."""
    try:
        # Run digest job in background
        background_tasks.add_task(run_digest_job)
        
        return {
            "success": True,
            "message": "Digest job started",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting digest job: {e}")
        raise HTTPException(status_code=500, detail="Failed to start digest job")

async def run_digest_job():
    """Background task to run the digest job."""
    try:
        repo = DigestRepo()
        config = DigestJobConfig()
        job = DigestJob(repo, config)
        
        result = await job.run_sweep()
        logger.info(f"Digest job completed: {result}")
    except Exception as e:
        logger.error(f"Digest job failed: {e}")

@router.get("/stats")
async def get_email_stats(
    days: int = 7,
    user_id: str = Depends(get_current_user_id),
    repo: DigestRepo = Depends()
):
    """Get email statistics."""
    try:
        stats = await repo.get_digest_stats(days)
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting email stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get email stats")

class TestEmailRequest(BaseModel):
    email: str

@router.post("/test")
async def send_test_email(
    request: TestEmailRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Send a test email to verify configuration."""
    try:
        email_sender_instance = email_sender()  # Get the instance
        result = await email_sender_instance.send_test_email(request.email)
        return {
            "success": result["success"],
            "message": "Test email sent" if result["success"] else "Failed to send test email",
            "details": result
        }
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test email")

@router.post("/webhooks/brevo")
async def brevo_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle Brevo webhook events."""
    try:
        # Parse webhook payload
        payload = await request.json()
        
        # Process webhook in background
        background_tasks.add_task(process_brevo_webhook, payload)
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error processing Brevo webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")

async def process_brevo_webhook(payload: Dict[str, Any]):
    """Process Brevo webhook payload."""
    try:
        repo = DigestRepo()
        
        # Extract event data
        event_type = payload.get("event")
        message_id = payload.get("message-id")
        email = payload.get("email")
        
        if not event_type or not message_id:
            logger.warning(f"Invalid webhook payload: {payload}")
            return
        
        # Get user_id from message_id if possible
        user_id = None
        # You might need to store message_id -> user_id mapping
        # or extract from custom headers
        
        # Log the event
        await repo.log_email_event(
            message_id=message_id,
            event=event_type,
            user_id=user_id,
            meta=payload
        )
        
        # Handle specific events
        if event_type in ["bounced", "spam"]:
            # Add to suppression list
            if email:
                email_sender_instance = email_sender()  # Get the instance
                await email_sender_instance.add_to_suppression_list(email, event_type)
        
        logger.info(f"Processed Brevo webhook: {event_type} for {message_id}")
        
    except Exception as e:
        logger.error(f"Error processing Brevo webhook: {e}")

# Add the router to your main FastAPI app
# app.include_router(email_router, prefix="/api/v1")

