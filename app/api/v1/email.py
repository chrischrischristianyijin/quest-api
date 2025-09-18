"""
Email API endpoints for digest system.
Handles preview, preferences, unsubscribe, and cron operations.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

# Import auth service for consistent authentication
from ...services.auth_service import AuthService

# Initialize auth service
auth_service = AuthService()

# Dependency to get current user - using the same approach as other routers
async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> str:
    """Get current user ID using the standard auth service."""
    try:
        logger.info(f"🔐 EMAIL API: Authenticating user with standard auth service")
        
        # Use the same authentication method as other routers
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        user_id = current_user.get("id")
        if not user_id:
            logger.error(f"🔐 EMAIL API: ❌ No user ID in auth response")
            raise HTTPException(status_code=401, detail="Invalid user data")
        
        logger.info(f"🔐 EMAIL API: ✅ Successfully authenticated user: {user_id}")
        return user_id
        
    except ValueError as ve:
        logger.error(f"🔐 EMAIL API: ❌ Auth service error: {ve}")
        raise HTTPException(status_code=401, detail=str(ve))
    except Exception as e:
        logger.error(f"🔐 EMAIL API: ❌ Authentication error: {e}")
        import traceback
        logger.error(f"🔐 EMAIL API: ❌ Traceback: {traceback.format_exc()}")
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
        logger.info(f"🔐 EMAIL API: Getting preferences for user: {user_id}")
        
        preferences = await repo.get_user_email_preferences(user_id)
        logger.info(f"🔐 EMAIL API: Retrieved preferences: {preferences}")
        
        if not preferences:
            logger.info(f"🔐 EMAIL API: No preferences found, creating default preferences for user: {user_id}")
            
            # Create default preferences for new user using service role key
            success = await repo.create_default_email_preferences(user_id)
            logger.info(f"🔐 EMAIL API: Create default preferences result: {success}")
            
            if not success:
                logger.error(f"🔐 EMAIL API: ❌ Failed to create default preferences for user: {user_id}")
                # Fall back to returning default preferences without database storage
                default_preferences = {
                    "weekly_digest_enabled": False,  # Start with disabled by default
                    "preferred_day": 1,  # Monday
                    "preferred_hour": 9,  # 9 AM
                    "timezone": "America/Los_Angeles",  # Default timezone
                    "no_activity_policy": "skip"  # Skip if no activity
                }
                
                result = {
                    "success": True,
                    "preferences": default_preferences
                }
                logger.info(f"🔐 EMAIL API: ✅ Returning fallback default preferences: {result}")
                return result
            
            # Get the newly created preferences
            preferences = await repo.get_user_email_preferences(user_id)
            logger.info(f"🔐 EMAIL API: Retrieved new preferences: {preferences}")
            
            if not preferences:
                logger.error(f"🔐 EMAIL API: ❌ Failed to retrieve preferences after creation for user: {user_id}")
                raise HTTPException(status_code=500, detail="Failed to retrieve preferences after creation")
        
        result = {
            "success": True,
            "preferences": {
                "weekly_digest_enabled": preferences["weekly_digest_enabled"],
                "preferred_day": preferences["preferred_day"],
                "preferred_hour": preferences["preferred_hour"],
                "timezone": preferences["timezone"],
                "no_activity_policy": preferences["no_activity_policy"]
            }
        }
        logger.info(f"🔐 EMAIL API: ✅ Returning stored preferences: {result}")
        return result
        
    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        logger.error(f"🔐 EMAIL API: ❌ Error getting email preferences: {e}")
        import traceback
        logger.error(f"🔐 EMAIL API: ❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get email preferences: {str(e)}")

@router.put("/preferences")
async def update_email_preferences(
    preferences: EmailPreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
    repo: DigestRepo = Depends()
):
    """Update user's email preferences."""
    try:
        logger.info(f"🔐 EMAIL API: Updating preferences for user: {user_id}")
        
        # Convert to dict and remove None values
        prefs_dict = preferences.dict(exclude_unset=True)
        logger.info(f"🔐 EMAIL API: Preferences to update: {prefs_dict}")
        
        # Update preferences in the database using the service role key
        success = await repo.update_user_email_preferences(user_id, prefs_dict)
        if not success:
            logger.error(f"🔐 EMAIL API: ❌ Failed to update preferences in database for user: {user_id}")
            raise HTTPException(status_code=500, detail="Failed to update preferences")
        
        logger.info(f"🔐 EMAIL API: ✅ Successfully updated preferences in database for user: {user_id}")
        return {
            "success": True,
            "message": "Email preferences updated successfully"
        }
        
    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        logger.error(f"🔐 EMAIL API: ❌ Error updating email preferences: {e}")
        import traceback
        logger.error(f"🔐 EMAIL API: ❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to update email preferences: {str(e)}")

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
        
        # Get user profile data from database
        user_profile = await repo.get_user_profile_data(user_id)
        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Combine user profile with preferences
        user_data = {
            "id": user_profile["id"],
            "email": user_profile["email"],
            "first_name": user_profile["first_name"],
            "nickname": user_profile.get("nickname"),
            "username": user_profile.get("username"),
            "avatar_url": user_profile.get("avatar_url"),
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
        
        # Generate content using the correct service and method signature
        from app.services.digest_content import DigestContentGenerator
        content_generator = DigestContentGenerator()
        payload = content_generator.build_user_digest_payload(
            user_data, 
            insights, 
            stacks, 
            user_prefs["no_activity_policy"]
        )
        
        # Render email content using the correct service
        from app.services.digest_job import DigestJob
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
    user_id: str = Depends(get_current_user_id),
    repo: DigestRepo = Depends()
):
    """Send a test digest email with real user data."""
    try:
        logger.info(f"🧪 TEST EMAIL: Generating test digest for user: {user_id}")
        
        # Get user data
        user_prefs = await repo.get_user_email_preferences(user_id)
        if not user_prefs:
            raise HTTPException(status_code=404, detail="User preferences not found")
        
        # Get user profile data from database
        user_profile = await repo.get_user_profile_data(user_id)
        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Combine user profile with preferences
        user_data = {
            "id": user_profile["id"],
            "email": user_profile["email"],
            "first_name": user_profile["first_name"],
            "nickname": user_profile.get("nickname"),
            "username": user_profile.get("username"),
            "avatar_url": user_profile.get("avatar_url"),
            "timezone": user_prefs["timezone"]
        }
        
        logger.info(f"🧪 TEST EMAIL: User data prepared for {user_data.get('first_name', 'User')}")
        
        # Generate digest content using the correct service
        from app.services.digest_content import DigestContentGenerator
        content_generator = DigestContentGenerator()
        
        # Get user activity data for the digest
        from datetime import datetime, timezone, timedelta
        from app.utils.time_utils import get_week_boundaries
        now_utc = datetime.now(timezone.utc)
        week_boundaries = get_week_boundaries(now_utc, user_prefs["timezone"])
        week_start = week_boundaries["prev_week_start"].date()
        start_utc = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_utc = start_utc.replace(hour=23, minute=59, second=59) + timedelta(days=6)
        
        insights, stacks = await repo.get_user_activity(user_id, start_utc, end_utc)
        digest_payload = content_generator.build_user_digest_payload(
            user_data, 
            insights, 
            stacks, 
            user_prefs["no_activity_policy"]
        )
        
        logger.info(f"🧪 TEST EMAIL: Digest payload generated with {len(digest_payload.get('insights', []))} insights")
        
        # Send the actual digest email to the test address
        from app.services.digest_job import DigestJob
        job = DigestJob(repo)
        
        # Override the email address for testing
        test_user_data = user_data.copy()
        test_user_data["email"] = request.email
        
        result = await job.send_digest_email(test_user_data, digest_payload)
        
        return {
            "success": result["success"],
            "message": f"Test digest email sent to {request.email}" if result["success"] else "Failed to send test digest",
            "details": {
                "insights_count": len(digest_payload.get('insights', [])),
                "user_name": user_data.get('first_name', 'User'),
                "test_email": request.email
            }
        }
    except Exception as e:
        logger.error(f"🧪 TEST EMAIL: ❌ Error sending test digest: {e}")
        import traceback
        logger.error(f"🧪 TEST EMAIL: ❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to send test digest: {str(e)}")

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

