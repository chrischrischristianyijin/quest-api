"""
Email sending service using Brevo (Sendinblue) API.
Handles email delivery, error handling, and deliverability tracking.
"""
import os
import httpx
import logging
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
import json
import hashlib
import secrets
import pytz
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Email preferences and decision logic
NoActivityPolicy = Literal["skip", "brief", "suggestions"]

@dataclass
class EmailPrefs:
    weekly_digest_enabled: bool
    preferred_day: int           # 0=Mon ... 6=Sun  (Python weekday)
    preferred_hour: int          # 0..23
    timezone: str                # e.g. "Asia/Tokyo"
    no_activity_policy: NoActivityPolicy  # "skip" | "brief" | "suggestions"

def should_send_weekly_digest(
    now_utc: datetime,
    prefs: EmailPrefs,
    has_insights: bool,
) -> bool:
    """
    Return True iff we should send right now.
    
    Args:
        now_utc: Current UTC datetime
        prefs: User email preferences
        has_insights: Whether user has recent insights
    
    Returns:
        True if should send, False otherwise
    """
    if not prefs.weekly_digest_enabled:
        return False

    tz = pytz.timezone(prefs.timezone or "UTC")
    now_local = now_utc.astimezone(tz)

    # Match exact hour + weekday in user's TZ
    weekday_match = now_local.weekday() == prefs.preferred_day
    hour_match = now_local.hour == prefs.preferred_hour

    if not (weekday_match and hour_match):
        return False

    # No activity policy
    if not has_insights and prefs.no_activity_policy == "skip":
        return False

    return True

class EmailSender:
    """Handles email sending via Brevo API."""
    
    def __init__(self):
        self.api_key = os.getenv("BREVO_API_KEY")
        self.base_url = "https://api.brevo.com/v3"
        self.sender_email = os.getenv("SENDER_EMAIL", "contact@myquestspace.com")
        self.sender_name = os.getenv("SENDER_NAME", "Quest")
        self.unsubscribe_base_url = os.getenv("UNSUBSCRIBE_BASE_URL", "https://myquestspace.com")
        
        # Don't raise error during initialization - check during actual usage
        self._api_key_available = bool(self.api_key)
    
    async def send_weekly_digest(
        self,
        to_email: str,
        user_id: str,
        subject: str,
        html_content: str,
        text_content: str,
        template_vars: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send a weekly digest email.
        
        Args:
            to_email: Recipient email address
            user_id: User ID for tracking
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content
            template_vars: Template variables for personalization
            headers: Additional headers
        
        Returns:
            Dict with send result including message_id
        """
        try:
            # Generate unsubscribe token
            unsubscribe_token = await self._get_or_create_unsubscribe_token(user_id)
            unsubscribe_url = f"{self.unsubscribe_base_url}/unsubscribe?token={unsubscribe_token}"
            
            # Prepare headers
            email_headers = {
                "List-Unsubscribe": f"<{unsubscribe_url}>, <mailto:unsubscribe@quest.example.com>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                "X-Quest-Digest-User": user_id,
                "X-Quest-Digest-Type": "weekly",
                "X-Quest-Digest-Date": datetime.utcnow().isoformat(),
                **(headers or {})
            }
            
            # Prepare email payload
            email_data = {
                "sender": {
                    "name": self.sender_name,
                    "email": self.sender_email
                },
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content,
                "textContent": text_content,
                "headers": email_headers,
                "params": template_vars,
                "tags": ["weekly-digest", "automated"],
                "replyTo": {
                    "email": "support@quest.example.com",
                    "name": "Quest Support"
                }
            }
            
            # Send via Brevo API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/smtp/email",
                    headers={
                        "api-key": self.api_key,
                        "accept": "application/json",
                        "content-type": "application/json"
                    },
                    json=email_data
                )
                
                response.raise_for_status()
                result = response.json()
                
                message_id = result.get("messageId", "")
                
                logger.info(f"Email sent successfully to {to_email}, message_id: {message_id}")
                
                return {
                    "success": True,
                    "message_id": message_id,
                    "to_email": to_email,
                    "sent_at": datetime.utcnow().isoformat(),
                    "unsubscribe_url": unsubscribe_url
                }
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(f"Email send failed for {to_email}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "to_email": to_email,
                "sent_at": datetime.utcnow().isoformat()
            }
            
        except httpx.RequestError as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(f"Email send failed for {to_email}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "to_email": to_email,
                "sent_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Email send failed for {to_email}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "to_email": to_email,
                "sent_at": datetime.utcnow().isoformat()
            }
    
    async def send_template_email(
        self,
        to_email: str,
        template_id: int,
        template_vars: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email using a Brevo template.
        
        Args:
            to_email: Recipient email address
            template_id: Brevo template ID
            template_vars: Template variables
            user_id: User ID for tracking
        
        Returns:
            Dict with send result
        """
        try:
            # Generate unsubscribe token if user_id provided
            unsubscribe_url = None
            if user_id:
                unsubscribe_token = await self._get_or_create_unsubscribe_token(user_id)
                unsubscribe_url = f"{self.unsubscribe_base_url}/unsubscribe?token={unsubscribe_token}"
            
            # Prepare email payload
            email_data = {
                "templateId": template_id,
                "to": [{"email": to_email}],
                "params": template_vars,
                "headers": {
                    "X-Quest-User": user_id or "anonymous"
                }
            }
            
            if unsubscribe_url:
                email_data["headers"]["List-Unsubscribe"] = f"<{unsubscribe_url}>, <mailto:unsubscribe@quest.example.com>"
            
            # Send via Brevo API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/smtp/email",
                    headers={
                        "api-key": self.api_key,
                        "accept": "application/json",
                        "content-type": "application/json"
                    },
                    json=email_data
                )
                
                response.raise_for_status()
                result = response.json()
                
                message_id = result.get("messageId", "")
                
                logger.info(f"Template email sent successfully to {to_email}, message_id: {message_id}")
                
                return {
                    "success": True,
                    "message_id": message_id,
                    "to_email": to_email,
                    "sent_at": datetime.utcnow().isoformat(),
                    "template_id": template_id
                }
                
        except Exception as e:
            error_msg = f"Template email send failed: {str(e)}"
            logger.error(f"Template email send failed for {to_email}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "to_email": to_email,
                "sent_at": datetime.utcnow().isoformat(),
                "template_id": template_id
            }
    
    async def send_brevo_digest(
        self,
        to_email: str,
        to_name: str,
        template_params: Dict[str, Any],
        template_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a weekly digest using Brevo template with structured logging.
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name
            template_params: Template parameters (should include "params" key)
            template_id: Brevo template ID (uses env var if not provided)
        
        Returns:
            Dict with send result including message_id
        """
        try:
            if not self._api_key_available:
                return {
                    "success": False,
                    "error": "BREVO_API_KEY environment variable is required"
                }
            
            # Use template ID from env or parameter
            template_id = template_id or int(os.getenv("BREVO_TEMPLATE_ID", "0"))
            if not template_id:
                return {
                    "success": False,
                    "error": "BREVO_TEMPLATE_ID environment variable is required"
                }
            
            # Prepare email payload
            email_data = {
                "templateId": template_id,
                "to": [{"email": to_email, "name": to_name}],
                "params": template_params,
                "headers": {
                    "X-Quest-Digest": "weekly",
                    "X-Quest-User": to_email
                },
                "tags": ["quest-weekly-digest"]
            }
            
            # Send via Brevo API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/smtp/email",
                    headers={
                        "api-key": self.api_key,
                        "accept": "application/json",
                        "content-type": "application/json"
                    },
                    json=email_data
                )
                
                response.raise_for_status()
                result = response.json()
                
                message_id = result.get("messageId", "")
                
                # Structured logging for observability
                logger.info("brevo_send_ok", extra={
                    "message_id": message_id,
                    "to": to_email,
                    "template_id": template_id,
                    "digest_type": "weekly"
                })
                
                return {
                    "success": True,
                    "message_id": message_id,
                    "to_email": to_email,
                    "sent_at": datetime.utcnow().isoformat(),
                    "template_id": template_id
                }
                
        except Exception as e:
            error_msg = f"Brevo digest send failed: {str(e)}"
            logger.error(f"Brevo digest send failed for {to_email}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "to_email": to_email,
                "sent_at": datetime.utcnow().isoformat()
            }
    
    async def send_test_email(
        self,
        to_email: str,
        subject: str = "Quest Test Email",
        content: str = "This is a test email from Quest."
    ) -> Dict[str, Any]:
        """
        Send a test email to verify configuration.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            content: Email content
        
        Returns:
            Dict with send result
        """
        return await self.send_weekly_digest(
            to_email=to_email,
            user_id="test",
            subject=subject,
            html_content=f"<html><body><h1>{subject}</h1><p>{content}</p></body></html>",
            text_content=content,
            template_vars={},
            headers={"X-Quest-Test": "true"}
        )
    
    async def _get_or_create_unsubscribe_token(self, user_id: str) -> str:
        """
        Get or create an unsubscribe token for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Unsubscribe token
        """
        # This would typically query your database
        # For now, we'll generate a deterministic token
        # In production, store this in the unsubscribe_tokens table
        
        # Create a deterministic but secure token
        secret_key = os.getenv("UNSUBSCRIBE_SECRET_KEY", "default-secret-key")
        token_data = f"{user_id}:{secret_key}"
        token = hashlib.sha256(token_data.encode()).hexdigest()[:32]
        
        return token
    
    async def check_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """
        Check the delivery status of an email.
        
        Args:
            message_id: Brevo message ID
        
        Returns:
            Dict with delivery status
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/smtp/emails/{message_id}",
                    headers={
                        "api-key": self.api_key,
                        "accept": "application/json"
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "message_id": message_id,
                    "status": result.get("status"),
                    "delivered_at": result.get("deliveredAt"),
                    "opened_at": result.get("openedAt"),
                    "clicked_at": result.get("clickedAt"),
                    "bounced_at": result.get("bouncedAt"),
                    "spam_at": result.get("spamAt")
                }
                
        except Exception as e:
            logger.error(f"Failed to check delivery status for {message_id}: {e}")
            return {
                "success": False,
                "message_id": message_id,
                "error": str(e)
            }
    
    async def get_suppression_list(self) -> List[Dict[str, Any]]:
        """
        Get the list of suppressed email addresses.
        
        Returns:
            List of suppressed emails
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/smtp/suppressions",
                    headers={
                        "api-key": self.api_key,
                        "accept": "application/json"
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                return result.get("suppressions", [])
                
        except Exception as e:
            logger.error(f"Failed to get suppression list: {e}")
            return []
    
    async def add_to_suppression_list(self, email: str, reason: str = "manual") -> Dict[str, Any]:
        """
        Add an email to the suppression list.
        
        Args:
            email: Email address to suppress
            reason: Reason for suppression
        
        Returns:
            Dict with result
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/smtp/suppressions",
                    headers={
                        "api-key": self.api_key,
                        "accept": "application/json",
                        "content-type": "application/json"
                    },
                    json={
                        "email": email,
                        "reason": reason
                    }
                )
                
                response.raise_for_status()
                
                logger.info(f"Added {email} to suppression list: {reason}")
                
                return {
                    "success": True,
                    "email": email,
                    "reason": reason
                }
                
        except Exception as e:
            logger.error(f"Failed to add {email} to suppression list: {e}")
            return {
                "success": False,
                "email": email,
                "error": str(e)
            }
    
    async def send_test_email(self, email: str) -> Dict[str, Any]:
        """
        Send a test email to verify configuration.
        
        Args:
            email: Test email address
        
        Returns:
            Result dictionary with success status
        """
        try:
            if not self._api_key_available:
                return {
                    "success": False,
                    "error": "BREVO_API_KEY environment variable is required"
                }
            
            if not self.validate_email_address(email):
                return {
                    "success": False,
                    "error": "Invalid email address format"
                }
            
            # Test email content
            subject = "Quest Email Test"
            html_content = """
            <html>
            <body>
                <h2>Quest Email Test</h2>
                <p>This is a test email from Quest to verify your email configuration.</p>
                <p>If you received this email, your email system is working correctly!</p>
                <p>Time: {}</p>
            </body>
            </html>
            """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
            
            text_content = f"""
            Quest Email Test
            
            This is a test email from Quest to verify your email configuration.
            
            If you received this email, your email system is working correctly!
            
            Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}
            """
            
            # Send via Brevo API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/smtp/email",
                    headers={
                        "api-key": self.api_key,
                        "accept": "application/json",
                        "content-type": "application/json"
                    },
                    json={
                        "sender": {
                            "name": self.sender_name,
                            "email": self.sender_email
                        },
                        "to": [{"email": email, "name": "Test User"}],
                        "subject": subject,
                        "htmlContent": html_content,
                        "textContent": text_content
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Test email sent successfully to {email}")
                
                return {
                    "success": True,
                    "messageId": result.get("messageId"),
                    "email": email
                }
                
        except Exception as e:
            logger.error(f"Failed to send test email to {email}: {e}")
            return {
                "success": False,
                "error": str(e),
                "email": email
            }

    def validate_email_address(self, email: str) -> bool:
        """
        Validate an email address format.
        
        Args:
            email: Email address to validate
        
        Returns:
            True if valid, False otherwise
        """
        import re
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get Brevo account information.
        
        Returns:
            Dict with account info
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/account",
                    headers={
                        "api-key": self.api_key,
                        "accept": "application/json"
                    }
                )
                
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "account": result
                }
                
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Global email sender instance - lazy initialization
_email_sender_instance = None

def get_email_sender():
    """Get the email sender instance (lazy initialization)."""
    global _email_sender_instance
    if _email_sender_instance is None:
        _email_sender_instance = EmailSender()
    return _email_sender_instance

# For backward compatibility
email_sender = get_email_sender