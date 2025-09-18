"""
Webhook handler for Brevo email events.
Processes delivery, bounce, and engagement events for analytics and suppression.
"""
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import hmac
import hashlib

from .digest_repo import DigestRepo
from .email_sender import email_sender

logger = logging.getLogger(__name__)

class BrevoWebhookHandler:
    """Handles Brevo webhook events for email tracking."""
    
    def __init__(self, repo: DigestRepo):
        self.repo = repo
        self.webhook_secret = None  # Set if you want to verify webhook signatures
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a Brevo webhook payload.
        
        Args:
            payload: Webhook payload from Brevo
        
        Returns:
            Processing result
        """
        try:
            event_type = payload.get("event")
            message_id = payload.get("message-id")
            email = payload.get("email")
            timestamp = payload.get("date")
            
            if not event_type or not message_id:
                logger.warning(f"Invalid webhook payload: missing required fields")
                return {"success": False, "error": "Invalid payload"}
            
            # Parse timestamp
            event_time = None
            if timestamp:
                try:
                    event_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp {timestamp}: {e}")
                    event_time = datetime.now(timezone.utc)
            else:
                event_time = datetime.now(timezone.utc)
            
            # Get user_id from message_id (you might need to implement this mapping)
            user_id = await self._get_user_id_from_message_id(message_id)
            
            # Log the event
            await self.repo.log_email_event(
                message_id=message_id,
                event=event_type,
                user_id=user_id,
                meta={
                    "email": email,
                    "timestamp": timestamp,
                    "raw_payload": payload
                }
            )
            
            # Handle specific event types
            result = await self._handle_event_type(event_type, message_id, email, user_id, payload)
            
            logger.info(f"Processed webhook event: {event_type} for {message_id}")
            return {
                "success": True,
                "event_type": event_type,
                "message_id": message_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_event_type(
        self, 
        event_type: str, 
        message_id: str, 
        email: str, 
        user_id: Optional[str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle specific event types."""
        
        if event_type == "delivered":
            return await self._handle_delivered(message_id, email, user_id, payload)
        
        elif event_type == "opened":
            return await self._handle_opened(message_id, email, user_id, payload)
        
        elif event_type == "clicked":
            return await self._handle_clicked(message_id, email, user_id, payload)
        
        elif event_type == "bounced":
            return await self._handle_bounced(message_id, email, user_id, payload)
        
        elif event_type == "spam":
            return await self._handle_spam(message_id, email, user_id, payload)
        
        elif event_type == "unsubscribed":
            return await self._handle_unsubscribed(message_id, email, user_id, payload)
        
        elif event_type == "blocked":
            return await self._handle_blocked(message_id, email, user_id, payload)
        
        else:
            logger.info(f"Unhandled event type: {event_type}")
            return {"status": "unhandled", "event_type": event_type}
    
    async def _handle_delivered(
        self, 
        message_id: str, 
        email: str, 
        user_id: Optional[str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle email delivered event."""
        logger.info(f"Email delivered: {message_id} to {email}")
        
        # Update digest status if we can find it
        if user_id:
            await self._update_digest_status(user_id, message_id, "delivered")
        
        return {"status": "delivered", "email": email}
    
    async def _handle_opened(
        self, 
        message_id: str, 
        email: str, 
        user_id: Optional[str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle email opened event."""
        logger.info(f"Email opened: {message_id} by {email}")
        
        # Track engagement
        if user_id:
            await self._track_engagement(user_id, "opened", message_id)
        
        return {"status": "opened", "email": email}
    
    async def _handle_clicked(
        self, 
        message_id: str, 
        email: str, 
        user_id: Optional[str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle email clicked event."""
        clicked_url = payload.get("url", "")
        logger.info(f"Email clicked: {message_id} by {email}, URL: {clicked_url}")
        
        # Track engagement
        if user_id:
            await self._track_engagement(user_id, "clicked", message_id, {"url": clicked_url})
        
        return {"status": "clicked", "email": email, "url": clicked_url}
    
    async def _handle_bounced(
        self, 
        message_id: str, 
        email: str, 
        user_id: Optional[str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle email bounced event."""
        bounce_type = payload.get("reason", "unknown")
        logger.warning(f"Email bounced: {message_id} to {email}, reason: {bounce_type}")
        
        # Add to suppression list
        await email_sender.add_to_suppression_list(email, "bounce")
        
        # Update digest status
        if user_id:
            await self._update_digest_status(user_id, message_id, "bounced")
        
        return {"status": "bounced", "email": email, "reason": bounce_type}
    
    async def _handle_spam(
        self, 
        message_id: str, 
        email: str, 
        user_id: Optional[str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle email marked as spam event."""
        logger.warning(f"Email marked as spam: {message_id} by {email}")
        
        # Add to suppression list
        await email_sender.add_to_suppression_list(email, "complaint")
        
        # Update digest status
        if user_id:
            await self._update_digest_status(user_id, message_id, "spam")
        
        return {"status": "spam", "email": email}
    
    async def _handle_unsubscribed(
        self, 
        message_id: str, 
        email: str, 
        user_id: Optional[str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle user unsubscribed event."""
        logger.info(f"User unsubscribed: {email}")
        
        # Disable digest for user
        if user_id:
            await self.repo.disable_user_digest(user_id)
        
        # Add to suppression list
        await email_sender.add_to_suppression_list(email, "unsubscribe")
        
        return {"status": "unsubscribed", "email": email}
    
    async def _handle_blocked(
        self, 
        message_id: str, 
        email: str, 
        user_id: Optional[str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle email blocked event."""
        block_reason = payload.get("reason", "unknown")
        logger.warning(f"Email blocked: {message_id} to {email}, reason: {block_reason}")
        
        # Add to suppression list
        await email_sender.add_to_suppression_list(email, "bounce")
        
        # Update digest status
        if user_id:
            await self._update_digest_status(user_id, message_id, "blocked")
        
        return {"status": "blocked", "email": email, "reason": block_reason}
    
    async def _get_user_id_from_message_id(self, message_id: str) -> Optional[str]:
        """
        Get user_id from message_id.
        
        This is a placeholder implementation. In production, you might:
        1. Store message_id -> user_id mapping in a separate table
        2. Include user_id in custom headers when sending
        3. Use a different approach based on your system
        """
        try:
            # Query email_digests table for message_id
            # This assumes you store message_id in the digest records
            response = self.repo.supabase.table("email_digests").select("user_id").eq("message_id", message_id).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.warning(f"Error finding user for message {message_id}: {response.error}")
                return None
            
            data = response.data or []
            if data:
                return data[0]["user_id"]
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting user_id for message {message_id}: {e}")
            return None
    
    async def _update_digest_status(
        self, 
        user_id: str, 
        message_id: str, 
        status: str
    ) -> bool:
        """Update digest status based on email event."""
        try:
            # Find digest by user_id and message_id
            response = self.repo.supabase.table("email_digests").select("id").eq("user_id", user_id).eq("message_id", message_id).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.warning(f"Error finding digest for user {user_id}, message {message_id}: {response.error}")
                return False
            
            data = response.data or []
            if not data:
                logger.warning(f"No digest found for user {user_id}, message {message_id}")
                return False
            
            digest_id = data[0]["id"]
            
            # Update status
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            update_response = self.repo.supabase.table("email_digests").update(update_data).eq("id", digest_id).execute()
            
            if hasattr(update_response, 'error') and update_response.error:
                logger.error(f"Error updating digest status: {update_response.error}")
                return False
            
            logger.info(f"Updated digest {digest_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating digest status: {e}")
            return False
    
    async def _track_engagement(
        self, 
        user_id: str, 
        engagement_type: str, 
        message_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Track user engagement with emails."""
        try:
            # This could be stored in a separate engagement tracking table
            # For now, we'll just log it
            logger.info(f"User {user_id} {engagement_type} email {message_id}")
            
            # You might want to:
            # 1. Store engagement data in a separate table
            # 2. Update user engagement metrics
            # 3. Use this data for personalization
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking engagement: {e}")
            return False
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature for security.
        
        Args:
            payload: Raw webhook payload
            signature: Signature from webhook headers
        
        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping signature verification")
            return True
        
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    async def get_delivery_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get email delivery statistics."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Get event counts
            response = self.repo.supabase.table("email_events").select("event").gte("occurred_at", cutoff_date.isoformat()).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error getting delivery stats: {response.error}")
                return {}
            
            events = response.data or []
            event_counts = {}
            for event in events:
                event_type = event["event"]
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            # Calculate rates
            total_sent = event_counts.get("delivered", 0) + event_counts.get("bounced", 0) + event_counts.get("blocked", 0)
            delivery_rate = (event_counts.get("delivered", 0) / total_sent * 100) if total_sent > 0 else 0
            bounce_rate = (event_counts.get("bounced", 0) / total_sent * 100) if total_sent > 0 else 0
            open_rate = (event_counts.get("opened", 0) / event_counts.get("delivered", 1) * 100) if event_counts.get("delivered", 0) > 0 else 0
            click_rate = (event_counts.get("clicked", 0) / event_counts.get("delivered", 1) * 100) if event_counts.get("delivered", 0) > 0 else 0
            
            return {
                "period_days": days,
                "total_sent": total_sent,
                "delivered": event_counts.get("delivered", 0),
                "bounced": event_counts.get("bounced", 0),
                "blocked": event_counts.get("blocked", 0),
                "opened": event_counts.get("opened", 0),
                "clicked": event_counts.get("clicked", 0),
                "spam": event_counts.get("spam", 0),
                "unsubscribed": event_counts.get("unsubscribed", 0),
                "delivery_rate": round(delivery_rate, 2),
                "bounce_rate": round(bounce_rate, 2),
                "open_rate": round(open_rate, 2),
                "click_rate": round(click_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting delivery stats: {e}")
            return {}

