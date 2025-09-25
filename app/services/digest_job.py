"""
Idempotent weekly digest job system.
Handles scheduling, content generation, and email sending with proper status transitions.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from dataclasses import dataclass

from .digest_time import should_send_now, compute_window, get_week_boundaries
from .digest_content import DigestContentGenerator
from .email_sender import email_sender
from .digest_repo import DigestRepo

logger = logging.getLogger(__name__)

@dataclass
class DigestJobConfig:
    """Configuration for digest job execution."""
    max_retries: int = 3
    retry_delay: int = 300  # 5 minutes
    batch_size: int = 50
    timeout: int = 30  # seconds per email
    dry_run: bool = False

class DigestJob:
    """Handles the execution of weekly digest jobs."""
    
    def __init__(self, repo: DigestRepo, config: Optional[DigestJobConfig] = None):
        self.repo = repo
        self.config = config or DigestJobConfig()
        self.content_generator = DigestContentGenerator()
    
    async def run_sweep(self, now_utc: Optional[datetime] = None, force_send: bool = False) -> Dict[str, Any]:
        """
        Run the digest sweep for all eligible users.
        
        Args:
            now_utc: Current UTC time (for testing)
            force_send: If True, bypass scheduling logic and send to all eligible users
        
        Returns:
            Dict with sweep results
        """
        if now_utc is None:
            now_utc = datetime.now(timezone.utc)
        
        if force_send:
            logger.info(f"🚀 Starting FORCE digest sweep at {now_utc.isoformat()} - bypassing scheduling logic")
        else:
            logger.info(f"Starting digest sweep at {now_utc.isoformat()}")
        
        try:
            # Get all users eligible for digest
            eligible_users = await self.repo.get_sendable_users(now_utc)
            logger.info(f"Found {len(eligible_users)} eligible users")
            
            if not eligible_users:
                return {
                    "success": True,
                    "processed": 0,
                    "sent": 0,
                    "skipped": 0,
                    "failed": 0,
                    "message": "No eligible users found"
                }
            
            # Process users in batches
            results = {
                "processed": 0,
                "sent": 0,
                "skipped": 0,
                "failed": 0,
                "errors": []
            }
            
            for i in range(0, len(eligible_users), self.config.batch_size):
                batch = eligible_users[i:i + self.config.batch_size]
                batch_results = await self._process_batch(batch, now_utc, force_send)
                
                # Aggregate results
                for key in ["processed", "sent", "skipped", "failed"]:
                    results[key] += batch_results[key]
                results["errors"].extend(batch_results.get("errors", []))
                
                # Small delay between batches to avoid rate limiting
                if i + self.config.batch_size < len(eligible_users):
                    await asyncio.sleep(1)
            
            logger.info(f"Digest sweep completed: {results}")
            return {
                "success": True,
                "timestamp": now_utc.isoformat(),
                **results
            }
            
        except Exception as e:
            logger.error(f"Digest sweep failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": now_utc.isoformat()
            }
    
    async def _process_batch(self, users: List[Dict[str, Any]], now_utc: datetime, force_send: bool = False) -> Dict[str, Any]:
        """Process a batch of users."""
        results = {
            "processed": 0,
            "sent": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }
        
        for user in users:
            try:
                result = await self._process_user(user, now_utc, force_send)
                results["processed"] += 1
                results[result["status"]] += 1
                
                if result.get("error"):
                    results["errors"].append({
                        "user_id": user.get("id"),
                        "error": result["error"]
                    })
                    
            except Exception as e:
                logger.error(f"Error processing user {user.get('id', 'unknown')}: {e}")
                results["processed"] += 1
                results["failed"] += 1
                results["errors"].append({
                    "user_id": user.get("id"),
                    "error": str(e)
                })
        
        return results
    
    async def _process_user(self, user: Dict[str, Any], now_utc: datetime, force_send: bool = False) -> Dict[str, Any]:
        """
        Process a single user for digest sending.
        
        Args:
            user: User data with preferences
            now_utc: Current UTC time
        
        Returns:
            Dict with processing result
        """
        user_id = user.get("id")
        email = user.get("email")
        timezone_str = user.get("timezone", "America/Los_Angeles")
        preferred_day = user.get("preferred_day", 6)  # Saturday
        preferred_hour = user.get("preferred_hour", 20)  # 8 PM
        no_activity_policy = user.get("no_activity_policy", "skip")
        
        try:
            # Check if it's time to send (skip this check in force mode)
            if not force_send and not should_send_now(timezone_str, preferred_day, preferred_hour, now_utc):
                logger.info(f"⏰ Skipping user {user_id} - not send time (timezone: {timezone_str}, day: {preferred_day}, hour: {preferred_hour})")
                return {
                    "status": "skipped",
                    "reason": "not_send_time",
                    "user_id": user_id
                }
            
            # Get week boundaries
            week_boundaries = get_week_boundaries(now_utc, timezone_str)
            week_start = week_boundaries["prev_week_start"].date()
            
            # Check idempotency - has digest already been sent for this week? (skip in force mode)
            existing_digest = await self.repo.get_digest_by_user_week(user_id, week_start)
            if existing_digest and not force_send:
                if existing_digest["status"] == "sent":
                    logger.info(f"Digest already sent for user {user_id}, week {week_start} - skipping")
                    return {
                        "status": "skipped",
                        "reason": "already_sent",
                        "user_id": user_id,
                        "digest_id": existing_digest["id"]
                    }
                elif existing_digest["status"] == "failed":
                    # Retry failed digest
                    logger.info(f"Retrying failed digest for user {user_id}")
                else:
                    # Digest in progress, skip
                    logger.info(f"Digest in progress for user {user_id}, week {week_start} - skipping")
                    return {
                        "status": "skipped",
                        "reason": "in_progress",
                        "user_id": user_id,
                        "digest_id": existing_digest["id"]
                    }
            
            # Create or update digest record
            digest_id = await self._create_or_update_digest_record(
                user_id, week_start, "queued", existing_digest
            )
            
            # Generate content
            logger.info(f"📝 Generating digest content for user {user_id}, week {week_start}")
            content_result = await self._generate_digest_content(
                user, week_boundaries, no_activity_policy
            )
            
            if not content_result["success"]:
                logger.error(f"❌ Content generation failed for user {user_id}: {content_result['error']}")
                await self.repo.update_digest(
                    digest_id, "failed", error=content_result["error"]
                )
                return {
                    "status": "failed",
                    "reason": "content_generation_failed",
                    "user_id": user_id,
                    "error": content_result["error"]
                }
            
            logger.info(f"✅ Content generated successfully for user {user_id}")
            
            # Check if we should skip sending (no activity policy)
            if content_result.get("skip_sending", False):
                await self.repo.update_digest(
                    digest_id, "sent", 
                    payload=content_result["payload"],
                    message_id="skipped"
                )
                return {
                    "status": "skipped",
                    "reason": "no_activity_skip",
                    "user_id": user_id,
                    "digest_id": digest_id
                }
            
            # Render email content
            render_result = await self._render_email_content(content_result["payload"])
            if not render_result["success"]:
                await self.repo.update_digest(
                    digest_id, "failed", error=render_result["error"]
                )
                return {
                    "status": "failed",
                    "reason": "render_failed",
                    "user_id": user_id,
                    "error": render_result["error"]
                }
            
            # Update digest status to rendered
            await self.repo.update_digest(
                digest_id, "rendered", payload=content_result["payload"]
            )
            
            # Send email (unless dry run)
            if self.config.dry_run:
                logger.info(f"DRY RUN: Would send email to {email}")
                await self.repo.update_digest(
                    digest_id, "sent", 
                    payload=content_result["payload"],
                    message_id="dry_run"
                )
                return {
                    "status": "sent",
                    "reason": "dry_run",
                    "user_id": user_id,
                    "digest_id": digest_id
                }
            
            # Send actual email
            logger.info(f"📧 Sending digest email to user {user_id} ({user.get('email', 'unknown')})")
            send_result = await self._send_digest_email(
                user, render_result, content_result["payload"]
            )
            
            if send_result["success"]:
                logger.info(f"✅ Email sent successfully to user {user_id}, message_id: {send_result['message_id']}")
                await self.repo.update_digest(
                    digest_id, "sent",
                    message_id=send_result["message_id"],
                    payload=content_result["payload"]
                )
                return {
                    "status": "sent",
                    "reason": "email_sent",
                    "user_id": user_id,
                    "digest_id": digest_id,
                    "message_id": send_result["message_id"]
                }
            else:
                logger.error(f"❌ Email send failed for user {user_id}: {send_result['error']}")
                await self.repo.update_digest(
                    digest_id, "failed", error=send_result["error"]
                )
                return {
                    "status": "failed",
                    "reason": "email_send_failed",
                    "user_id": user_id,
                    "error": send_result["error"]
                }
                
        except Exception as e:
            import traceback
            error_details = {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "user_id": user_id,
                "email": user.get("email", "unknown"),
                "timezone": timezone_str,
                "preferred_day": preferred_day,
                "preferred_hour": preferred_hour
            }
            logger.error(f"❌ Error processing user {user_id}: {error_details}")
            return {
                "status": "failed",
                "reason": "unexpected_error",
                "user_id": user_id,
                "error": str(e),
                "error_details": error_details
            }
    
    async def _create_or_update_digest_record(
        self, 
        user_id: str, 
        week_start: datetime.date, 
        status: str,
        existing_digest: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create or update digest record."""
        try:
            if existing_digest:
                logger.info(f"📝 Updating existing digest record {existing_digest['id']} for user {user_id}, week {week_start} to status {status}")
                await self.repo.update_digest(
                    existing_digest["id"], status
                )
                return existing_digest["id"]
            else:
                logger.info(f"📝 Creating new digest record for user {user_id}, week {week_start} with status {status}")
                return await self.repo.create_digest_record(user_id, week_start, status)
        except Exception as e:
            logger.error(f"❌ Error in _create_or_update_digest_record for user {user_id}, week {week_start}: {e}")
            logger.error(f"❌ Existing digest: {existing_digest}")
            raise
    
    async def _generate_digest_content(
        self, 
        user: Dict[str, Any], 
        week_boundaries: Dict[str, Any],
        no_activity_policy: str
    ) -> Dict[str, Any]:
        """Generate digest content for user."""
        try:
            user_id = user["id"]
            start_utc = week_boundaries["prev_week_start"]
            end_utc = week_boundaries["prev_week_end"]
            
            # Get user activity for the week
            insights, stacks = await self.repo.get_user_activity(user_id, start_utc, end_utc)
            
            # Debug logging for insights
            logger.info(f"Retrieved {len(insights)} insights and {len(stacks)} stacks for user {user_id}")
            for i, insight in enumerate(insights[:3]):  # Log first 3 insights
                logger.info(f"Insight {i+1}: '{insight.get('title', 'No title')}' with tags: {insight.get('tags', [])}")
            
            # Generate content
            payload = self.content_generator.build_user_digest_payload(
                user, insights, stacks, no_activity_policy
            )
            
            # Generate AI summary if insights are available
            if insights and len(insights) > 0:
                try:
                    ai_summary = await self.repo.get_ai_summary(insights, user_id)
                    payload["ai_summary"] = ai_summary
                    logger.info(f"Generated AI summary for user {user_id}: {len(ai_summary)} characters")
                except Exception as e:
                    logger.error(f"Error generating AI summary for user {user_id}: {e}")
                    payload["ai_summary"] = "AI summary temporarily unavailable."
            else:
                payload["ai_summary"] = "No insights available for AI summary this week."
            
            # Debug logging for payload structure
            logger.info(f"Payload sections keys: {list(payload.get('sections', {}).keys())}")
            logger.info(f"Tags section data: {payload.get('sections', {}).get('tags', [])}")
            logger.info(f"AI summary length: {len(payload.get('ai_summary', ''))}")
            
            # Check if we should skip sending
            skip_sending = (
                payload.get("metadata", {}).get("skipped", False) or
                payload.get("metadata", {}).get("brief_mode", False) and 
                no_activity_policy == "skip"
            )
            
            return {
                "success": True,
                "payload": payload,
                "skip_sending": skip_sending,
                "insights_count": len(insights),
                "stacks_count": len(stacks)
            }
            
        except Exception as e:
            logger.error(f"Error generating digest content for user {user.get('id')}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _render_email_content(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Render email content from payload."""
        try:
            # This would typically use a template engine like Jinja2
            # For now, we'll create a simple HTML template
            
            user = payload["user"]
            sections = payload["sections"]
            activity_summary = payload["activity_summary"]
            
            # Generate subject
            if activity_summary["total_activity"] > 0:
                total_insights = activity_summary.get("total_insights", 0)
                subject = f"Your Weekly Quest Digest - {total_insights} new insights"
            else:
                subject = "Your Weekly Quest Digest"
            
            # Generate HTML content
            html_content = self._generate_html_content(payload)
            
            # Generate text content
            text_content = self._generate_text_content(payload)
            
            return {
                "success": True,
                "subject": subject,
                "html_content": html_content,
                "text_content": text_content
            }
            
        except Exception as e:
            logger.error(f"Error rendering email content: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_html_content(self, payload: Dict[str, Any]) -> str:
        """Generate HTML email content."""
        user = payload["user"]
        sections = payload["sections"]
        activity_summary = payload["activity_summary"]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Your Weekly Quest Digest</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .section {{ margin-bottom: 30px; }}
                .section h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                .item {{ background: #fff; border: 1px solid #e1e8ed; border-radius: 6px; padding: 15px; margin-bottom: 15px; }}
                .item h3 {{ margin: 0 0 10px 0; color: #2c3e50; }}
                .item p {{ margin: 0 0 10px 0; color: #666; }}
                .item a {{ color: #3498db; text-decoration: none; }}
                .item a:hover {{ text-decoration: underline; }}
                .footer {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; font-size: 12px; color: #666; }}
                .stats {{ background: #e8f4fd; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
                .unsubscribe {{ margin-top: 20px; font-size: 11px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Hello {user['first_name']}! 👋</h1>
                <p>Here's your weekly Quest digest</p>
            </div>
            
            <div class="stats">
                <h3>This Week's Activity</h3>
                <p>📝 {activity_summary.get('total_insights', 0)} insights • 📚 {activity_summary.get('total_stacks', 0)} stacks</p>
            </div>
        """
        
        # Add highlights section
        highlights = sections.get("highlights", {})
        if highlights.get("items"):
            html += f"""
            <div class="section">
                <h2>{highlights['title']}</h2>
            """
            for item in highlights["items"]:
                html += f"""
                <div class="item">
                    <h3>{item['title']}</h3>
                    <p>{item.get('summary', '')}</p>
                    {f'<p><a href="{item["url"]}" target="_blank">Read more →</a></p>' if item.get('url') else ''}
                </div>
                """
            html += "</div>"
        
        # Add more content section
        more_content = sections.get("more_content", {})
        if more_content.get("items"):
            html += f"""
            <div class="section">
                <h2>{more_content['title']}</h2>
            """
            for item in more_content["items"]:
                html += f"""
                <div class="item">
                    <h3>{item['title']}</h3>
                    {f'<p><a href="{item["url"]}" target="_blank">Read more →</a></p>' if item.get('url') else ''}
                </div>
                """
            html += "</div>"
        
        # Add suggestions section
        suggestions = sections.get("suggestions", {})
        if suggestions.get("items"):
            html += f"""
            <div class="section">
                <h2>{suggestions['title']}</h2>
            """
            for item in suggestions["items"]:
                html += f"""
                <div class="item">
                    <h3>{item['title']}</h3>
                    <p>{item.get('description', '')}</p>
                    {f'<p><a href="{item["url"]}" target="_blank">{item.get("action", "Learn more")} →</a></p>' if item.get('url') else ''}
                </div>
                """
            html += "</div>"
        
        html += """
            <div class="footer">
                <p>Thanks for using Quest! Keep building your knowledge base.</p>
                <div class="unsubscribe">
                    <p><a href="{{unsubscribe_url}}">Unsubscribe</a> | <a href="https://quest.example.com/settings">Email Preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_text_content(self, payload: Dict[str, Any]) -> str:
        """Generate plain text email content."""
        user = payload["user"]
        sections = payload["sections"]
        activity_summary = payload["activity_summary"]
        
        text = f"""
Hello {user['first_name']}!

Here's your weekly Quest digest:

This Week's Activity:
- {activity_summary['total_insights']} insights
- {activity_summary['total_stacks']} stacks

"""
        
        # Add highlights
        highlights = sections.get("highlights", {})
        if highlights.get("items"):
            text += f"\n{highlights['title']}:\n"
            for item in highlights["items"]:
                text += f"- {item['title']}\n"
                if item.get('summary'):
                    text += f"  {item['summary']}\n"
                if item.get('url'):
                    text += f"  {item['url']}\n"
                text += "\n"
        
        # Add more content
        more_content = sections.get("more_content", {})
        if more_content.get("items"):
            text += f"\n{more_content['title']}:\n"
            for item in more_content["items"]:
                text += f"- {item['title']}\n"
                if item.get('url'):
                    text += f"  {item['url']}\n"
                text += "\n"
        
        # Add suggestions
        suggestions = sections.get("suggestions", {})
        if suggestions.get("items"):
            text += f"\n{suggestions['title']}:\n"
            for item in suggestions["items"]:
                text += f"- {item['title']}\n"
                if item.get('description'):
                    text += f"  {item['description']}\n"
                if item.get('url'):
                    text += f"  {item['url']}\n"
                text += "\n"
        
        text += """
Thanks for using Quest! Keep building your knowledge base.

Unsubscribe: {{unsubscribe_url}}
Email Preferences: https://quest.example.com/settings
"""
        
        return text
    
    async def _send_digest_email(
        self, 
        user: Dict[str, Any], 
        render_result: Dict[str, Any],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send the digest email using Brevo template."""
        try:
            # Use Brevo template instead of HTML generation
            # Flatten tags and other template-expected fields to top level
            template_params = {
                "params": {
                    **payload,  # Include all payload data
                    "tags": payload.get("sections", {}).get("tags", []),  # Flatten tags to top level
                    "login_url": "https://myquestspace.com/login",
                    "unsubscribe_url": "https://myquestspace.com/unsubscribe"
                },
                "user": payload.get("user", {}),
                "sections": payload.get("sections", {}),
                "activity_summary": payload.get("activity_summary", {}),
                "metadata": payload.get("metadata", {})
            }

            result = await email_sender().send_brevo_digest(
                to_email=user["email"],
                to_name=user.get("first_name", "there"),
                template_params=template_params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending digest email to {user['email']}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_digest_email(
        self, 
        user_data: Dict[str, Any], 
        digest_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Public method to send a digest email (for testing purposes).
        
        Args:
            user_data: User information including email
            digest_payload: Generated digest content
        
        Returns:
            Dict with send result
        """
        try:
            # Render the email content
            render_result = await self._render_email_content(digest_payload)
            if not render_result["success"]:
                return {
                    "success": False,
                    "error": f"Failed to render email: {render_result['error']}"
                }
            
            # Send the email
            send_result = await self._send_digest_email(
                user_data, render_result, digest_payload
            )
            
            return send_result
            
        except Exception as e:
            logger.error(f"Error in send_digest_email: {e}")
            return {
                "success": False,
                "error": str(e)
            }

