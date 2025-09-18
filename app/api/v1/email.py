"""
Email API endpoints for digest system.
Handles preview, preferences, unsubscribe, and cron operations.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import hmac
import hashlib

from ...services.digest_repo import DigestRepo
from ...services.digest_job import DigestJob, DigestJobConfig
from ...services.digest_content import DigestContentGenerator
from ...services.digest_time import get_week_boundaries
from ...services.email_sender import email_sender
from ...core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])

# Setup Jinja2 template environment
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)

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

def build_context(user_profile: dict, user_prefs: dict, tags_list, ai_summary, rec_tag, rec_articles, login_url, unsubscribe_url):
    """Build template context for digest rendering."""
    # safe display name
    display_name = (
        user_profile.get("first_name")
        or user_profile.get("nickname")
        or user_profile.get("username")
        or "there"
    )
    contact = {"FIRSTNAME": display_name}

    params = {
        "tags": tags_list or [],
        "ai_summary": ai_summary or None,
        "recommended_tag": rec_tag or None,
        "recommended_articles": rec_articles or None,
        "login_url": login_url or "#",
        "unsubscribe_url": unsubscribe_url or "#",
    }
    return {"contact": contact, "params": params}

def render_digest_html(context: dict) -> str:
    """Render digest HTML using Jinja2 template."""
    template = env.get_template("weekly_digest.jinja2")
    return template.render(**context)

def _build_params(user: dict, insights: list) -> dict:
    """Build template parameters for digest rendering."""
    from ...services.digest_repo import DigestRepo
    repo = DigestRepo()
    
    tags = repo.summarize_by_tag(insights)
    ai_summary = repo.get_ai_summary(insights)
    rec_tag, rec_articles = repo.get_recommended_content(user["id"])
    
    return {
        "tags": tags,  # list of {"name","articles"}
        "ai_summary": ai_summary,
        "recommended_tag": rec_tag,
        "recommended_articles": rec_articles,
        "login_url": f"{settings.APP_BASE_URL}/login",
        "unsubscribe_url": f"{settings.UNSUBSCRIBE_BASE_URL}?u={user['id']}",
    }

def _preview_html(params: dict) -> str:
    """
    Build a standalone HTML that mirrors the template structure,
    but without any template parsing - plain string assembly.
    """
    # Build tag blocks
    tag_blocks = []
    for tag in (params.get("tags") or []):
        tag_name = tag.get("name", "Untagged")
        tag_articles = tag.get("articles", "—")
        tag_blocks.append(
            f'''<div style="margin:15px 0;padding:10px;background-color:#f9fafb;border-left:4px solid #2563eb;">
                 <strong>{tag_name}</strong>: {tag_articles}
               </div>'''
        )
    
    if not tag_blocks:
        tag_blocks = ["""<div style="margin:15px 0;padding:10px;background-color:#f9fafb;border-left:4px solid #2563eb;">
          No tagged items this week—save some insights to see them here next time.
        </div>"""]

    ai_summary = params.get("ai_summary") or "Your AI summary will appear here once generated."
    rec_tag = params.get("recommended_tag") or "topics"
    rec_articles = params.get("recommended_articles") or "—"
    login_url = params.get("login_url", "#")
    unsubscribe_url = params.get("unsubscribe_url", "#")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Weekly Digest Preview</title></head>
<body style="margin:0;padding:20px;background:#ffffff;font-family:Arial,Helvetica,sans-serif;line-height:1.6;color:#333;">
  <div style="max-width:600px;margin:0 auto;">
    <h2 style="color:#2563eb;margin:0 0 16px;">My Quest Space Weekly Knowledge Digest</h2>
    <p>Hi there,</p>
    <p>To better utilize your second brain, please check out the following knowledge review report!</p>
    <h3 style="color:#1f2937;margin-top:30px;">This Week's Collection:</h3>
    {''.join(tag_blocks)}
    <h3 style="color:#1f2937;margin-top:30px;">AI Summary:</h3>
    <div style="background-color:#f0f9ff;padding:15px;border-radius:8px;margin:15px 0;">{ai_summary}</div>
    <h3 style="color:#1f2937;margin-top:30px;">This Week's Recommendations:</h3>
    <p>Your followed <strong>{rec_tag}</strong> featured articles this week: {rec_articles}</p>
    <div style="text-align:center;margin:40px 0;">
      <a href="{login_url}" target="_blank" rel="noopener" style="background-color:#2563eb;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:6px;display:inline-block;">
        Open Quest – Login to Review Your Knowledge Base
      </a>
    </div>
    <p style="text-align:center;color:#6b7280;font-style:italic;margin-top:30px;">
      Your second brain is not a storage repository, but a thinking accelerator
    </p>
    <hr style="margin:40px 0;border:none;border-top:1px solid #e5e7eb;">
    <div style="text-align:center;font-size:12px;color:#9ca3af;">
      <p>
        <a href="{unsubscribe_url}" target="_blank" rel="noopener" style="color:#6b7280;">Unsubscribe</a> |
        <a href="mailto:support@quest.example.com" style="color:#6b7280;">Contact Support</a>
      </p>
      <p>&copy; 2025 Quest. All rights reserved.</p>
    </div>
  </div>
</body></html>"""

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
async def digest_preview_post(payload: dict, user_id: str = Depends(get_current_user_id)):
    """
    Returns JSON with html_content, for clients that expect JSON.
    Simplified version that avoids template parsing issues.
    """
    try:
        # Get user profile data
        repo = DigestRepo()
        user_profile = await repo.get_user_profile_data(user_id)
        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get recent insights (tolerate empty insight sets)
        insights = await repo.get_recent_insights(user_id, days=7) or []
        
        # Build parameters using safe methods
        params = _build_params(user_profile, insights)
        
        # Generate simple HTML preview without template parsing
        html = _preview_html(params)

        return JSONResponse({
            "success": True,
            "preview": {
                "subject": "Your Weekly Knowledge Digest (Preview)",
                "html_content": html,
                "text_content": "",  # optional: convert html->text if you like
                "payload": {
                    "tags_count": len(params.get("tags", [])),
                }
            }
        }, status_code=200)

    except Exception as e:
        logger.error(f"digest preview POST failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse({"success": False, "message": "Failed to generate HTML preview"}, status_code=500)

@router.get("/digest/preview", response_class=HTMLResponse)
async def digest_preview_get(user_id: str = Depends(get_current_user_id)):
    """
    Returns raw HTML for preview (used by the modal GET path).
    Simplified version that avoids template parsing issues.
    """
    try:
        # Get user profile data
        repo = DigestRepo()
        user_profile = await repo.get_user_profile_data(user_id)
        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get recent insights (tolerate empty insight sets)
        insights = await repo.get_recent_insights(user_id, days=7) or []
        
        # Build parameters using safe methods
        params = _build_params(user_profile, insights)
        
        # Generate simple HTML preview without template parsing
        html = _preview_html(params)
        
        # Return HTML with explicit content type
        return HTMLResponse(content=html, status_code=200)

    except Exception as e:
        logger.error(f"digest preview GET failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Return readable HTML even on errors
        return HTMLResponse(
            content="<html><body style='font-family:Arial;padding:24px'>Failed to generate HTML preview.</body></html>",
            status_code=500
        )

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
            "first_name": user_profile.get("first_name") or user_profile.get("nickname") or "User",
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

