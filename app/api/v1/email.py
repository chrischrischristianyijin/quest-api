"""
Email API endpoints for digest system.
Handles preview, preferences, unsubscribe, and cron operations.
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, Query
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
from ...services.email_sender import email_sender, EmailPrefs, should_send_weekly_digest
from ...core.config import settings
from typing import Any, Dict, List
import pytz

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

def _safe_list(x) -> List[Any]:
    """Safely convert to list, handling None and other types."""
    return x if isinstance(x, list) else []

def _safe_str(x) -> str:
    """Safely convert to string, handling None and other types."""
    return x if isinstance(x, str) else ""

def _summarize_by_tag(insights: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Safely summarize insights by tag with defensive programming."""
    tags_map: Dict[str, List[str]] = {}
    for it in _safe_list(insights):
        title = _safe_str(it.get("title")) or "Untitled"
        insight_tags = _safe_list(it.get("tags"))
        
        # Debug logging
        logger.info(f"📧 TAG DEBUG: Processing insight '{title}' with tags: {insight_tags}")
        
        if not insight_tags:
            # Handle insights without tags
            tags_map.setdefault("Untagged", []).append(title)
        else:
            for t in insight_tags:
                name = _safe_str(t.get("name")) if isinstance(t, dict) else _safe_str(t)
                if not name:
                    name = "Untagged"
                tags_map.setdefault(name, []).append(title)
                logger.info(f"📧 TAG DEBUG: Added '{title}' to tag '{name}'")
    
    result = [{"name": k, "articles": ", ".join(v[:6])} for k, v in tags_map.items()]
    logger.info(f"📧 TAG DEBUG: Final tags summary: {result}")
    return result

def _build_params(user: dict, insights: list) -> dict:
    """Build template parameters for digest rendering with defensive programming."""
    from ...services.digest_repo import DigestRepo
    repo = DigestRepo()
    
    # Use safe summarization
    tags = _summarize_by_tag(insights)
    
    # Keep AI summary/recommendation defensive if repo returns None
    try:
        ai_summary = _safe_str(repo.get_ai_summary(insights, user.get("id")))
    except Exception:
        ai_summary = ""
    
    try:
        rec = repo.get_recommended_content(user.get("id"))
        if not isinstance(rec, tuple) or len(rec) != 2:
            rec = ("", "")
    except Exception:
        rec = ("", "")
    rec_tag, rec_articles = rec
    
    return {
        "tags": tags,  # list of {"name","articles"}
        "ai_summary": ai_summary,
        "recommended_tag": _safe_str(rec_tag),
        "recommended_articles": _safe_str(rec_articles),
        "login_url": f"{settings.APP_BASE_URL}/login",
        "unsubscribe_url": f"{settings.UNSUBSCRIBE_BASE_URL}?u={_safe_str(user.get('id'))}",
    }

def _preview_html(params: dict) -> str:
    """
    Build a standalone HTML that mirrors the template structure,
    but without any template parsing - plain string assembly.
    """
    # Build tag blocks with safe helpers
    tag_blocks: List[str] = []
    for t in _safe_list(params.get("tags")):
        nm = _safe_str(t.get("name")) or "Untagged"
        arts = _safe_str(t.get("articles")) or "—"
        tag_blocks.append(
            f'''<div style="margin:15px 0;padding:10px;background-color:#f9fafb;border-left:4px solid #2563eb;">
  <strong>{nm}</strong>: {arts}
</div>'''
        )
    
    if not tag_blocks:
        tag_blocks = ["""<div style="margin:15px 0;padding:10px;background-color:#f9fafb;border-left:4px solid #2563eb;">
No tagged items this week—save some insights to see them here next time.
</div>"""]

    ai_summary = _safe_str(params.get("ai_summary")) or "Your AI summary will appear here once generated."
    rec_tag = _safe_str(params.get("recommended_tag")) or "topics"
    rec_articles = _safe_str(params.get("recommended_articles")) or "—"
    login_url = _safe_str(params.get("login_url")) or "#"
    unsubscribe_url = _safe_str(params.get("unsubscribe_url")) or "#"

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
                    "user_id": user_id,  # Include user_id
                    "weekly_digest_enabled": False,  # Start with disabled by default
                    "preferred_day": 6,  # Saturday
                    "preferred_hour": 20,  # 8 PM
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
                "user_id": preferences.get("user_id", user_id),  # Include user_id
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
            # Graceful fallback: create minimal profile data instead of failing
            logger.warning(f"📧 DIGEST PREVIEW: No profile found for user {user_id}, using fallback profile")
            user_profile = {
                "id": user_id,
                "email": "user@example.com",  # Fallback email
                "first_name": "User",
                "nickname": "User",
                "username": f"user_{user_id[:8]}",
                "avatar_url": None
            }
        
        # Get recent insights (tolerate empty insight sets)
        insights = await repo.get_recent_insights(user_id, days=7) or []
        
        # Build parameters using safe methods
        params = await _build_params(user_profile, insights)
        
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

@router.get("/digest/preview")
async def digest_preview_get(
    user_id: str = Depends(get_current_user_id),
    target_user_id: Optional[str] = Query(None, description="User ID to preview for (admin only)"),
    uid: Optional[str] = Query(None, description="Alias for target_user_id")
):
    """
    Returns JSON with html field for preview (used by the modal GET path).
    Hardened version that never 500s and always returns JSON.
    
    Args:
        user_id: Current authenticated user ID
        target_user_id: Optional user ID to preview for (admin only)
        uid: Alias for target_user_id (convenience parameter)
    """
    try:
        # Support both parameter names for convenience
        requested_target = target_user_id or uid
        preview_user_id = requested_target or user_id
        
        repo = DigestRepo()
        
        # Admin check only when previewing someone else
        if requested_target and requested_target != user_id:
            me = await repo.get_user_profile_data(user_id)
            if not (me and me.get("is_admin", False)):
                return JSONResponse({"ok": False, "error": "Admin access required"}, status_code=403)
        
        # 🔒 Always use preview_user_id below (never session user)
        user_profile = await repo.get_user_profile_data(preview_user_id) or {"id": preview_user_id, "first_name": "User"}
        insights = await repo.get_recent_insights(preview_user_id, days=7) or []
        
        # Build parameters using safe methods
        params = await _build_params(user_profile, insights)
        
        # Generate simple HTML preview without template parsing
        html = _preview_html(params)
        
        # Helpful diagnostics
        import hashlib, json
        params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        logger.info({
            "event": "digest_preview",
            "auth_user": user_id,
            "preview_user": preview_user_id,
            "insights_count": len(insights),
            "unsubscribe_url": params.get("unsubscribe_url"),
            "params_hash": params_hash
        })
        
        return JSONResponse({"ok": True, "html": html, "params": params}, status_code=200)

    except Exception as e:
        logger.error(f"digest preview GET failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # NEVER 500 — return a safe fallback
        fallback = _preview_html({
            "tags": [],
            "ai_summary": "",
            "recommended_tag": "",
            "recommended_articles": "",
            "login_url": f"{settings.APP_BASE_URL}/login",
            "unsubscribe_url": f"{settings.UNSUBSCRIBE_BASE_URL}?u={_safe_str(user_id)}",
        })
        return JSONResponse({"ok": False, "html": fallback, "error": str(e)}, status_code=200)

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
            # Graceful fallback: create minimal profile data instead of failing
            logger.warning(f"🧪 TEST EMAIL: No profile found for user {user_id}, using fallback profile")
            user_profile = {
                "id": user_id,
                "email": "user@example.com",  # Fallback email
                "first_name": "User",
                "nickname": "User",
                "username": f"user_{user_id[:8]}",
                "avatar_url": None
            }
        
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
        from app.services.digest_time import get_week_boundaries
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
        
        # Log test email event to database
        if result.get("success") and result.get("message_id"):
            try:
                # Log to email_events table
                await repo.log_email_event(
                    message_id=result["message_id"],
                    event="sent",
                    user_id=user_id,
                    meta={
                        "email_type": "test_digest",
                        "to_email": request.email,
                        "insights_count": len(digest_payload.get('insights', [])),
                        "test_send": True
                    }
                )
                
                # Note: email_digests table is redundant - all info is in email_events
                
                logger.info(f"📧 TEST EMAIL EVENT: Logged test email sent event for message {result['message_id']}")
            except Exception as e:
                logger.error(f"📧 TEST EMAIL EVENT: Failed to log test email event: {e}")
        
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

@router.post("/digest/test-send")
async def test_send_digest(
    force: bool = Query(False),
    dry_run: bool = Query(True),
    email_override: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id)
):
    """
    Test endpoint for digest sending logic.
    
    - dry_run=True: build everything but don't call Brevo
    - force=True: ignore schedule and send decision
    - email_override: send to this email instead of user's email (for testing)
    """
    try:
        repo = DigestRepo()
        
        # Get user preferences
        prefs_raw = await repo.get_user_email_preferences(user_id)
        if not prefs_raw:
            # Create default preferences if none exist
            await repo.create_default_email_preferences(user_id)
            prefs_raw = await repo.get_user_email_preferences(user_id)
        
        # Convert to EmailPrefs dataclass
        prefs = EmailPrefs(
            weekly_digest_enabled=prefs_raw.get("weekly_digest_enabled", True),
            preferred_day=int(prefs_raw.get("preferred_day", 0)),
            preferred_hour=int(prefs_raw.get("preferred_hour", 9)),
            timezone=prefs_raw.get("timezone", "UTC"),
            no_activity_policy=prefs_raw.get("no_activity_policy", "skip"),
        )

        # Resolve target user - if email_override is provided, find the user by email
        target_user_id = user_id
        if email_override:
            try:
                # Find user by email in auth.users table
                auth_response = repo.supabase_service.schema("auth").table("users").select("id,email").eq("email", email_override).limit(1).execute()
                
                if not auth_response.data:
                    return JSONResponse({
                        "ok": False, 
                        "error": f"No user found for email: {email_override}",
                        "decision": False,
                        "will_send": False
                    }, status_code=400)
                
                target_user_id = auth_response.data[0]["id"]
                logger.info(f"📧 EMAIL DIGEST DEBUG: Resolved email_override {email_override} to user_id {target_user_id}")
                
            except Exception as e:
                logger.error(f"📧 EMAIL DIGEST DEBUG: Failed to resolve email_override {email_override}: {e}")
                return JSONResponse({
                    "ok": False, 
                    "error": f"Failed to resolve email: {email_override}",
                    "decision": False,
                    "will_send": False
                }, status_code=400)
        
        insights = await repo.get_recent_insights(target_user_id, days=7) or []
        has_insights = len(insights) > 0
        
        # Debug logging
        logger.info(f"📧 EMAIL DIGEST DEBUG: auth_user_id={user_id}, target_user_id={target_user_id}, insights_count={len(insights)}, has_insights={has_insights}")
        logger.info(f"📧 EMAIL DIGEST DEBUG: force={force}, dry_run={dry_run}, email_override={email_override}")
        if insights:
            logger.info(f"📧 EMAIL DIGEST DEBUG: Sample insight: {insights[0]}")

        # Make decision
        now_utc = datetime.now(timezone.utc)
        decision = should_send_weekly_digest(now_utc, prefs, has_insights)
        logger.info(f"📧 EMAIL DIGEST DEBUG: decision={decision}, prefs={prefs}")

        will_send = force or decision
        
        result = {
            "decision": decision,
            "forced": force,
            "will_send": will_send,
            "prefs": prefs_raw,
            "stats": {
                "insights_count": len(insights),
                "has_insights": has_insights,
            },
            "mode": "dry_run" if dry_run else "real_send",
            "email_override": email_override,
            "current_time_utc": now_utc.isoformat(),
            "current_time_local": now_utc.astimezone(pytz.timezone(prefs.timezone)).isoformat(),
        }

        if not will_send:
            return JSONResponse({"ok": True, **result, "note": "Skipped by schedule/no_activity policy."}, 200)

        # Build template params using target user's data
        user_profile = await repo.get_user_profile_data(target_user_id)
        if not user_profile:
            user_profile = {"id": target_user_id, "first_name": "User"}
        
        params = await _build_params(user_profile, insights)
        result["params_sample"] = {k: (v if k != "tags" else v[:2]) for k, v in params.items()}
        
        # Debug logging for params
        logger.info(f"📧 EMAIL PARAMS: Built params with {len(params.get('tags', []))} tags")
        logger.info(f"📧 EMAIL PARAMS: AI summary: {params.get('ai_summary', 'None')[:100]}...")
        logger.info(f"📧 EMAIL PARAMS: Tags sample: {params.get('tags', [])[:2]}")

        if dry_run:
            return JSONResponse({"ok": True, **result, "note": "Dry run only. No email sent."}, 200)

        # Real send
        email_sender_instance = email_sender()
        
        # Debug: Log exactly what we're sending to Brevo
        logger.info(f"📧 BREVO SEND: Sending to {email_override or user_profile.get('email', 'test@example.com')}")
        logger.info(f"📧 BREVO SEND: Template params structure: {type(params)}")
        logger.info(f"📧 BREVO SEND: Template params keys: {list(params.keys()) if isinstance(params, dict) else 'Not a dict'}")
        logger.info(f"📧 BREVO SEND: Template params: {params}")
        
        # CORRECT: Wrap params under "params" key to match Brevo template structure
        template_params_wrapped = {"params": params}
        logger.info(f"📧 BREVO SEND: Wrapped params structure: {template_params_wrapped}")
        
        send_result = await email_sender_instance.send_brevo_digest(
            to_email=email_override or user_profile.get("email", "test@example.com"),
            to_name=user_profile.get("first_name", "User"),
            template_params=template_params_wrapped,  # Wrap under "params" to match template
        )
        
        # Log email event to database
        if send_result.get("success") and send_result.get("message_id"):
            try:
                # Log to email_events table
                await repo.log_email_event(
                    message_id=send_result["message_id"],
                    event="sent",
                    user_id=user_id,
                    meta={
                        "email_type": "weekly_digest",
                        "to_email": email_override or user_profile.get("email", "test@example.com"),
                        "template_id": send_result.get("template_id"),
                        "insights_count": len(insights),
                        "test_send": bool(email_override)
                    }
                )
                
                # Note: email_digests table is redundant - all info is in email_events
                
                logger.info(f"📧 EMAIL EVENT: Logged sent event for message {send_result['message_id']}")
            except Exception as e:
                logger.error(f"📧 EMAIL EVENT: Failed to log sent event: {e}")
        
        return JSONResponse({"ok": True, **result, "send_result": send_result}, 200)

    except Exception as e:
        logger.error(f"Test send digest failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse({"ok": False, "error": str(e)}, 500)

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

# Helper functions
def _safe_str(value) -> str:
    """Safely convert value to string."""
    if value is None:
        return ""
    return str(value).strip()

def _safe_list(value) -> list:
    """Safely convert value to list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]

def _summarize_by_tag(insights: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Safely summarize insights by tag with defensive programming."""
    tags_map: Dict[str, List[str]] = {}
    for it in _safe_list(insights):
        title = _safe_str(it.get("title")) or "Untitled"
        insight_tags = _safe_list(it.get("tags"))
        
        # Debug logging
        logger.info(f"📧 TAG DEBUG: Processing insight '{title}' with tags: {insight_tags}")
        
        if not insight_tags:
            # Handle insights without tags
            tags_map.setdefault("Untagged", []).append(title)
        else:
            for t in insight_tags:
                name = _safe_str(t.get("name")) if isinstance(t, dict) else _safe_str(t)
                if not name:
                    name = "Untagged"
                tags_map.setdefault(name, []).append(title)
                logger.info(f"📧 TAG DEBUG: Added '{title}' to tag '{name}'")
    
    result = [{"name": k, "articles": ", ".join(v[:6])} for k, v in tags_map.items()]
    logger.info(f"📧 TAG DEBUG: Final tags summary: {result}")
    return result

async def _build_params(user_profile: Dict[str, Any], insights: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build email template parameters from user profile and insights."""
    logger.info(f"📧 PARAMS BUILD: Processing {len(insights)} insights for user {user_profile.get('id', 'unknown')}")
    
    # Process insights by tags
    tags = _summarize_by_tag(insights)
    
    # Use AI summary service (same as the first _build_params function)
    from ...services.digest_repo import DigestRepo
    repo = DigestRepo()
    
    # Keep AI summary/recommendation defensive if repo returns None
    try:
        ai_summary = _safe_str(await repo.get_ai_summary(insights, user_profile.get("id")))
        logger.info(f"📧 PARAMS BUILD: AI summary generated successfully, length: {len(ai_summary)}")
    except Exception as e:
        logger.warning(f"📧 PARAMS BUILD: AI summary failed, using fallback: {e}")
        # Fallback to simple summary in Chinese
        insight_count = len(insights)
        if insight_count > 0:
            ai_summary = f"• 本周你捕获了{insight_count}个新洞察，继续扩展你的第二大脑！"
            if tags:
                tag_names = [tag["name"] for tag in tags]
                ai_summary += f"\n• 你的洞察被组织成{len(tags)}个类别：{', '.join(tag_names[:2])}{'...' if len(tag_names) > 2 else ''}"
                if len(tag_names) > 2:
                    ai_summary += f"\n• 主要关注领域：{tag_names[0]}和{tag_names[1]}"
        else:
            ai_summary = "• 本周没有新洞察，考虑添加一些内容来构建你的知识库！"
    
    try:
        rec = repo.get_recommended_content(user_profile.get("id"))
        if not isinstance(rec, tuple) or len(rec) != 2:
            rec = ("", "")
    except Exception:
        rec = ("", "")
    rec_tag, rec_articles = rec
    
    # Build parameters
    params = {
        "tags": tags,
        "ai_summary": ai_summary,
        "recommended_tag": _safe_str(rec_tag) if rec_tag else (tags[0]["name"] if tags else "General"),
        "recommended_articles": _safe_str(rec_articles) if rec_articles else (tags[0]["articles"] if tags else "Check out our latest insights"),
        "login_url": f"{settings.APP_BASE_URL}/my-space",
        "unsubscribe_url": f"{settings.UNSUBSCRIBE_BASE_URL}?u={_safe_str(user_profile.get('id'))}"
    }
    
    logger.info(f"📧 PARAMS BUILD: Built params with {len(tags)} tags, AI summary length: {len(ai_summary)}")
    return params


@router.get("/debug/ai-summary")
async def debug_ai_summary(user_id: str = Depends(get_current_user_id)):
    """Debug AI summary generation"""
    try:
        from app.services.ai_summary_service import get_ai_summary_service
        
        service = get_ai_summary_service()
        
        # Test health check
        is_healthy, health_msg = await service._health_check()
        
        # Test insights fetch
        insights = await service._get_weekly_insights(user_id)
        
        # Test full generation
        summary = await service.generate_weekly_insights_summary(user_id)
        
        return {
            "health_check": {"ok": is_healthy, "message": health_msg},
            "insights_count": len(insights),
            "summary": summary,
            "client_available": service.is_available(),
            "model": service.chat_model,
            "base_url": service.openai_base_url,
            "api_key_set": bool(service.openai_api_key)
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

@router.post("/digest/send-all")
async def send_digest_to_all_users(
    force: bool = Query(True),
    dry_run: bool = Query(False),
    confirmed: bool = Query(False),
    user_id: str = Depends(get_current_user_id)
):
    """
    Send digest emails to ALL eligible users immediately.
    
    ⚠️  ADMIN-ONLY ENDPOINT ⚠️
    This bypasses timing restrictions and sends personalized emails to all users
    who have weekly_digest_enabled=True.
    
    Args:
        force: Always True (bypasses timing)
        dry_run: If True, builds emails but doesn't send them
        confirmed: Must be True to actually send emails (safety measure)
        user_id: Current user ID (for authentication)
    
    Returns:
        Dict with results of the bulk send operation
    """
    try:
        # SECURITY CHECK 1: Require explicit confirmation
        if not confirmed and not dry_run:
            return {
                "success": False,
                "message": "⚠️ SAFETY CHECK: Add ?confirmed=true to confirm bulk email send",
                "warning": "This will send emails to ALL users. Use dry_run=true to test first.",
                "next_steps": [
                    "1. Test with: ?dry_run=true to see what would be sent",
                    "2. Confirm with: ?confirmed=true&dry_run=false to actually send"
                ]
            }
        
        # SECURITY CHECK 2: Get user profile to check for admin status
        repo = DigestRepo()
        user_profile = await repo.get_user_profile_data(user_id)
        
        # Debug logging
        logger.info(f"🔍 ADMIN DEBUG: user_profile = {user_profile}")
        logger.info(f"🔍 ADMIN DEBUG: is_admin field = {user_profile.get('is_admin') if user_profile else 'No profile'}")
        
        # Check if user has admin privileges
        is_admin = False
        if user_profile:
            # Option 1: Check for admin field in profile
            is_admin = user_profile.get("is_admin", False)
            logger.info(f"🔍 ADMIN DEBUG: is_admin result = {is_admin}")
            
            # Option 2: Check for specific email domains
            user_email = user_profile.get("email", "")
            if user_email:
                admin_domains = ["@quest.com", "@yourcompany.com"]  # Add your admin domains
                is_admin = any(user_email.endswith(domain) for domain in admin_domains)
        
        # SECURITY CHECK 3: Require admin access for non-dry-run
        if not dry_run and not is_admin:
            return {
                "success": False,
                "message": "❌ ACCESS DENIED: Admin privileges required for bulk email send",
                "user_id": user_id,
                "is_admin": is_admin,
                "note": "Only admins can send bulk emails. Contact system administrator."
            }
        
        logger.info(f"🚀 BULK SEND: Starting bulk digest send for all users (dry_run={dry_run}, admin={is_admin})")
        
        # Initialize services
        repo = DigestRepo()
        config = DigestJobConfig()
        job = DigestJob(repo, config)
        
        # Get current time for the sweep
        now_utc = datetime.now(timezone.utc)
        
        # Get all eligible users
        eligible_users = await repo.get_sendable_users(now_utc)
        logger.info(f"🚀 BULK SEND: Found {len(eligible_users)} eligible users")
        
        if not eligible_users:
            return {
                "success": True,
                "message": "No eligible users found",
                "processed": 0,
                "sent": 0,
                "skipped": 0,
                "failed": 0,
                "users": []
            }
        
        # If dry_run, just return the user list and what would be sent
        if dry_run:
            logger.info(f"🚀 BULK SEND: Dry run mode - would send to {len(eligible_users)} users")
            return {
                "success": True,
                "message": f"Dry run: Would send to {len(eligible_users)} users",
                "processed": len(eligible_users),
                "sent": 0,
                "skipped": 0,
                "failed": 0,
                "dry_run": True,
                "users": [
                    {
                        "id": user["id"],
                        "email": user["email"],
                        "first_name": user.get("first_name"),
                        "timezone": user.get("timezone")
                    }
                    for user in eligible_users
                ]
            }
        
        # Process users in batches to avoid overwhelming the system
        results = {
            "processed": 0,
            "sent": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
            "users": []
        }
        
        batch_size = 5  # Process 5 users at a time
        total_batches = (len(eligible_users) + batch_size - 1) // batch_size
        
        logger.info(f"🚀 BULK SEND: Processing {len(eligible_users)} users in {total_batches} batches of {batch_size}")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(eligible_users))
            batch = eligible_users[start_idx:end_idx]
            
            logger.info(f"🚀 BULK SEND: Processing batch {batch_num + 1}/{total_batches} ({len(batch)} users)")
            
            # Process each user in the batch
            for user in batch:
                try:
                    user_id = user["id"]
                    user_email = user["email"]
                    user_name = user.get("first_name", "User")
                    
                    logger.info(f"🚀 BULK SEND: Processing user {user_id} ({user_email})")
                    
                    # Get user's recent insights
                    insights = await repo.get_recent_insights(user_id, days=7) or []
                    has_insights = len(insights) > 0
                    
                    # Get user profile data
                    user_profile = await repo.get_user_profile_data(user_id)
                    if not user_profile:
                        user_profile = {
                            "id": user_id,
                            "first_name": user_name,
                            "email": user_email
                        }
                    
                    # Build email parameters
                    params = await _build_params(user_profile, insights)
                    
                    # Send email via Brevo
                    email_sender_instance = email_sender()
                    template_params_wrapped = {"params": params}
                    
                    send_result = await email_sender_instance.send_brevo_digest(
                        to_email=user_email,
                        to_name=user_name,
                        template_params=template_params_wrapped,
                    )
                    
                    if send_result.get("success"):
                        logger.info(f"✅ BULK SEND: Successfully sent to {user_email}")
                        results["sent"] += 1
                        
                        # Log email event
                        try:
                            await repo.log_email_event(
                                message_id=send_result["message_id"],
                                event="sent",
                                user_id=user_id,
                                meta={
                                    "email_type": "weekly_digest",
                                    "to_email": user_email,
                                    "template_id": send_result.get("template_id"),
                                    "insights_count": len(insights),
                                    "bulk_send": True
                                }
                            )
                        except Exception as e:
                            logger.error(f"⚠️ BULK SEND: Failed to log email event for {user_email}: {e}")
                        
                        results["users"].append({
                            "id": user_id,
                            "email": user_email,
                            "status": "sent",
                            "message_id": send_result.get("message_id"),
                            "insights_count": len(insights)
                        })
                    else:
                        logger.error(f"❌ BULK SEND: Failed to send to {user_email}: {send_result}")
                        results["failed"] += 1
                        results["errors"].append({
                            "user_id": user_id,
                            "email": user_email,
                            "error": send_result.get("error", "Unknown error")
                        })
                        results["users"].append({
                            "id": user_id,
                            "email": user_email,
                            "status": "failed",
                            "error": send_result.get("error", "Unknown error")
                        })
                    
                    results["processed"] += 1
                    
                    # Small delay between users to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"❌ BULK SEND: Error processing user {user.get('id', 'unknown')}: {e}")
                    results["failed"] += 1
                    results["errors"].append({
                        "user_id": user.get("id", "unknown"),
                        "email": user.get("email", "unknown"),
                        "error": str(e)
                    })
                    results["processed"] += 1
            
            # Delay between batches
            if batch_num < total_batches - 1:
                logger.info(f"🚀 BULK SEND: Waiting 2 seconds before next batch...")
                await asyncio.sleep(2)
        
        logger.info(f"🚀 BULK SEND: Completed! Processed: {results['processed']}, Sent: {results['sent']}, Failed: {results['failed']}")
        
        return {
            "success": True,
            "message": f"Bulk digest send completed. Processed: {results['processed']}, Sent: {results['sent']}, Failed: {results['failed']}",
            "processed": results["processed"],
            "sent": results["sent"],
            "skipped": results["skipped"],
            "failed": results["failed"],
            "errors": results["errors"],
            "users": results["users"],
            "timestamp": now_utc.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ BULK SEND: Bulk digest send failed: {e}")
        import traceback
        logger.error(f"❌ BULK SEND: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Bulk digest send failed: {str(e)}")

