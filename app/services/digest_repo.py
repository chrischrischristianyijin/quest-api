"""
Database repository for digest system.
Handles all database operations for email preferences, digests, and user activity.
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from supabase import create_client, Client
import os

logger = logging.getLogger(__name__)

class DigestRepo:
    """Repository for digest-related database operations."""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_anon_key or not self.supabase_service_key:
            raise ValueError("SUPABASE_URL, SUPABASE_ANON_KEY, and SUPABASE_SERVICE_ROLE_KEY environment variables are required")
        
        # Use ANON key for read operations
        self.supabase: Client = create_client(self.supabase_url, self.supabase_anon_key)
        # Use SERVICE ROLE key for write operations (create/update/delete)
        self.supabase_service: Client = create_client(self.supabase_url, self.supabase_service_key)
    
    async def get_sendable_users(self, now_utc: datetime) -> List[Dict[str, Any]]:
        """
        Get all users who are eligible for digest sending.
        
        Args:
            now_utc: Current UTC time
        
        Returns:
            List of user data with email preferences
        """
        try:
            # Query users with email preferences enabled
            response = self.supabase.table("email_preferences").select(
                """
                user_id,
                weekly_digest_enabled,
                preferred_day,
                preferred_hour,
                timezone,
                no_activity_policy,
                users!inner(
                    id,
                    email,
                    first_name,
                    name,
                    created_at
                )
                """
            ).eq("weekly_digest_enabled", True).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error fetching sendable users: {response.error}")
                return []
            
            users = []
            for pref in response.data or []:
                user_data = pref.get("users", {})
                if user_data and user_data.get("email"):
                    users.append({
                        "id": pref["user_id"],
                        "email": user_data["email"],
                        "first_name": user_data.get("first_name"),
                        "name": user_data.get("name"),
                        "timezone": pref["timezone"],
                        "preferred_day": pref["preferred_day"],
                        "preferred_hour": pref["preferred_hour"],
                        "no_activity_policy": pref["no_activity_policy"],
                        "created_at": user_data.get("created_at")
                    })
            
            logger.info(f"Found {len(users)} sendable users")
            return users
            
        except Exception as e:
            logger.error(f"Error fetching sendable users: {e}")
            return []
    
    async def get_user_activity(
        self, 
        user_id: str, 
        start_utc: datetime, 
        end_utc: datetime
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Get user activity (insights and stacks) for a time period.
        
        Args:
            user_id: User ID
            start_utc: Start time (UTC)
            end_utc: End time (UTC)
        
        Returns:
            Tuple of (insights, stacks)
        """
        try:
            # Get insights created/updated in the time window
            insights_response = self.supabase.table("insights").select(
                """
                id,
                title,
                description,
                url,
                image_url,
                created_at,
                updated_at,
                tags,
                stack_id,
                insight_contents(
                    summary,
                    thought
                )
                """
            ).eq("user_id", user_id).gte("updated_at", start_utc.isoformat()).lt("updated_at", end_utc.isoformat()).order("updated_at", desc=True).execute()
            
            if hasattr(insights_response, 'error') and insights_response.error:
                logger.error(f"Error fetching insights for user {user_id}: {insights_response.error}")
                insights = []
            else:
                insights = insights_response.data or []
            
            # Get stacks created/updated in the time window
            stacks_response = self.supabase.table("stacks").select(
                """
                id,
                name,
                description,
                created_at,
                updated_at
                """
            ).eq("user_id", user_id).gte("updated_at", start_utc.isoformat()).lt("updated_at", end_utc.isoformat()).order("updated_at", desc=True).execute()
            
            if hasattr(stacks_response, 'error') and stacks_response.error:
                logger.error(f"Error fetching stacks for user {user_id}: {stacks_response.error}")
                stacks = []
            else:
                stacks = stacks_response.data or []
            
            # Get stack item counts
            for stack in stacks:
                stack_id = stack["id"]
                items_response = self.supabase.table("insights").select("id").eq("stack_id", stack_id).execute()
                stack["item_count"] = len(items_response.data or []) if not hasattr(items_response, 'error') else 0
            
            logger.info(f"Found {len(insights)} insights and {len(stacks)} stacks for user {user_id}")
            return insights, stacks
            
        except Exception as e:
            logger.error(f"Error fetching user activity for {user_id}: {e}")
            return [], []
    
    async def get_digest_by_user_week(self, user_id: str, week_start: datetime.date) -> Optional[Dict[str, Any]]:
        """
        Get digest record for a user and week.
        
        Args:
            user_id: User ID
            week_start: Week start date
        
        Returns:
            Digest record or None
        """
        try:
            response = self.supabase.table("email_digests").select("*").eq("user_id", user_id).eq("week_start", week_start.isoformat()).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error fetching digest for user {user_id}, week {week_start}: {response.error}")
                return None
            
            data = response.data or []
            return data[0] if data else None
            
        except Exception as e:
            logger.error(f"Error fetching digest for user {user_id}, week {week_start}: {e}")
            return None
    
    async def create_digest_record(
        self, 
        user_id: str, 
        week_start: datetime.date, 
        status: str
    ) -> str:
        """
        Create a new digest record.
        
        Args:
            user_id: User ID
            week_start: Week start date
            status: Initial status
        
        Returns:
            Digest record ID
        """
        try:
            response = self.supabase_service.table("email_digests").insert({
                "user_id": user_id,
                "week_start": week_start.isoformat(),
                "status": status,
                "retry_count": 0
            }).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error creating digest record: {response.error}")
                raise Exception(f"Failed to create digest record: {response.error}")
            
            digest_id = response.data[0]["id"]
            logger.info(f"Created digest record {digest_id} for user {user_id}, week {week_start}")
            return digest_id
            
        except Exception as e:
            logger.error(f"Error creating digest record for user {user_id}: {e}")
            raise
    
    async def update_digest(
        self, 
        digest_id: str, 
        status: str, 
        message_id: Optional[str] = None,
        error: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a digest record.
        
        Args:
            digest_id: Digest record ID
            status: New status
            message_id: Brevo message ID
            error: Error message
            payload: Digest payload
        
        Returns:
            True if successful
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if message_id is not None:
                update_data["message_id"] = message_id
            
            if error is not None:
                update_data["error"] = error
                update_data["retry_count"] = self.supabase_service.rpc("increment_retry_count", {"digest_id": digest_id}).execute()
            
            if payload is not None:
                update_data["payload"] = payload
            
            response = self.supabase_service.table("email_digests").update(update_data).eq("id", digest_id).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error updating digest {digest_id}: {response.error}")
                return False
            
            logger.info(f"Updated digest {digest_id} to status {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating digest {digest_id}: {e}")
            return False
    
    async def get_user_email_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's email preferences.
        
        Args:
            user_id: User ID
        
        Returns:
            Email preferences or None
        """
        try:
            logger.info(f"🔐 DIGEST REPO: Fetching email preferences for user: {user_id}")
            
            # Use service role key for better access
            response = self.supabase_service.table("email_preferences").select("*").eq("user_id", user_id).execute()
            
            logger.info(f"🔐 DIGEST REPO: Fetch response: {response}")
            logger.info(f"🔐 DIGEST REPO: Response data: {response.data}")
            logger.info(f"🔐 DIGEST REPO: Response count: {response.count}")
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"🔐 DIGEST REPO: ❌ Supabase error fetching email preferences for user {user_id}: {response.error}")
                return None
            
            data = response.data or []
            result = data[0] if data else None
            logger.info(f"🔐 DIGEST REPO: Returning preferences: {result}")
            return result
            
        except Exception as e:
            logger.error(f"🔐 DIGEST REPO: ❌ Exception fetching email preferences for user {user_id}: {e}")
            import traceback
            logger.error(f"🔐 DIGEST REPO: ❌ Traceback: {traceback.format_exc()}")
            return None
    
    async def create_default_email_preferences(self, user_id: str) -> bool:
        """
        Create default email preferences for a new user.
        
        Args:
            user_id: User ID
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"🔐 DIGEST REPO: Creating default email preferences for user: {user_id}")
            
            default_preferences = {
                "user_id": user_id,
                "weekly_digest_enabled": True,
                "preferred_day": 1,  # Monday
                "preferred_hour": 9,  # 9 AM
                "timezone": "UTC",
                "no_activity_policy": "brief"
            }
            
            logger.info(f"🔐 DIGEST REPO: Default preferences data: {default_preferences}")
            
            response = self.supabase_service.table("email_preferences").insert(default_preferences).execute()
            
            logger.info(f"🔐 DIGEST REPO: Supabase response: {response}")
            logger.info(f"🔐 DIGEST REPO: Response data: {response.data}")
            logger.info(f"🔐 DIGEST REPO: Response count: {response.count}")
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"🔐 DIGEST REPO: ❌ Supabase error creating default email preferences for user {user_id}: {response.error}")
                return False
            
            if not response.data:
                logger.error(f"🔐 DIGEST REPO: ❌ No data returned from insert operation for user {user_id}")
                return False
            
            logger.info(f"🔐 DIGEST REPO: ✅ Created default email preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"🔐 DIGEST REPO: ❌ Exception creating default email preferences for user {user_id}: {e}")
            import traceback
            logger.error(f"🔐 DIGEST REPO: ❌ Traceback: {traceback.format_exc()}")
            return False
    
    async def update_user_email_preferences(
        self, 
        user_id: str, 
        preferences: Dict[str, Any]
    ) -> bool:
        """
        Update user's email preferences.
        
        Args:
            user_id: User ID
            preferences: Preferences to update
        
        Returns:
            True if successful
        """
        try:
            # Remove None values
            preferences = {k: v for k, v in preferences.items() if v is not None}
            
            # Add user_id to preferences for upsert
            preferences["user_id"] = user_id
            
            # Use upsert to create or update preferences
            response = self.supabase_service.table("email_preferences").upsert(preferences).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error updating email preferences for user {user_id}: {response.error}")                                                                                                        
                return False
            
            logger.info(f"Updated email preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating email preferences for user {user_id}: {e}")
            return False
    
    async def create_unsubscribe_token(self, user_id: str) -> str:
        """
        Create an unsubscribe token for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Unsubscribe token
        """
        try:
            import secrets
            token = secrets.token_urlsafe(32)
            
            response = self.supabase.table("unsubscribe_tokens").upsert({
                "user_id": user_id,
                "token": token
            }).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error creating unsubscribe token for user {user_id}: {response.error}")
                raise Exception(f"Failed to create unsubscribe token: {response.error}")
            
            logger.info(f"Created unsubscribe token for user {user_id}")
            return token
            
        except Exception as e:
            logger.error(f"Error creating unsubscribe token for user {user_id}: {e}")
            raise
    
    async def get_user_by_unsubscribe_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get user by unsubscribe token.
        
        Args:
            token: Unsubscribe token
        
        Returns:
            User data or None
        """
        try:
            response = self.supabase.table("unsubscribe_tokens").select(
                """
                user_id,
                users!inner(
                    id,
                    email,
                    first_name,
                    name
                )
                """
            ).eq("token", token).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error fetching user by unsubscribe token: {response.error}")
                return None
            
            data = response.data or []
            if data:
                user_data = data[0].get("users", {})
                return {
                    "id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "first_name": user_data.get("first_name"),
                    "name": user_data.get("name")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching user by unsubscribe token: {e}")
            return None
    
    async def disable_user_digest(self, user_id: str) -> bool:
        """
        Disable digest for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            True if successful
        """
        try:
            response = self.supabase.table("email_preferences").update({
                "weekly_digest_enabled": False
            }).eq("user_id", user_id).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error disabling digest for user {user_id}: {response.error}")
                return False
            
            logger.info(f"Disabled digest for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling digest for user {user_id}: {e}")
            return False
    
    async def log_email_event(
        self, 
        message_id: str, 
        event: str, 
        user_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log an email event from Brevo webhook.
        
        Args:
            message_id: Brevo message ID
            event: Event type
            user_id: User ID (if available)
            meta: Additional metadata
        
        Returns:
            True if successful
        """
        try:
            event_data = {
                "message_id": message_id,
                "event": event,
                "occurred_at": datetime.utcnow().isoformat()
            }
            
            if user_id:
                event_data["user_id"] = user_id
            
            if meta:
                event_data["meta"] = meta
            
            response = self.supabase.table("email_events").insert(event_data).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error logging email event: {response.error}")
                return False
            
            logger.info(f"Logged email event: {event} for message {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging email event: {e}")
            return False
    
    async def get_digest_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get digest statistics for the last N days.
        
        Args:
            days: Number of days to look back
        
        Returns:
            Statistics dictionary
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).date()
            
            # Get digest counts by status
            response = self.supabase.table("email_digests").select("status").gte("created_at", cutoff_date.isoformat()).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error fetching digest stats: {response.error}")
                return {}
            
            digests = response.data or []
            status_counts = {}
            for digest in digests:
                status = digest["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Get total users with preferences
            prefs_response = self.supabase.table("email_preferences").select("user_id").eq("weekly_digest_enabled", True).execute()
            total_users = len(prefs_response.data or []) if not hasattr(prefs_response, 'error') else 0
            
            return {
                "total_users": total_users,
                "digests_sent": status_counts.get("sent", 0),
                "digests_failed": status_counts.get("failed", 0),
                "digests_queued": status_counts.get("queued", 0),
                "digests_rendered": status_counts.get("rendered", 0),
                "total_digests": len(digests),
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error fetching digest stats: {e}")
            return {}

    async def get_user_profile_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile data for digest generation.
        
        Args:
            user_id: User ID
        
        Returns:
            User profile data or None
        """
        try:
            # Get user profile from profiles table using service role key
            response = self.supabase_service.table("profiles").select(
                """
                id,
                nickname,
                email,
                username,
                avatar_url,
                created_at,
                updated_at
                """
            ).eq("id", user_id).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error fetching user profile for {user_id}: {response.error}")
                return None
            
            data = response.data or []
            if not data:
                logger.warning(f"No user profile found for user {user_id}")
                return None
            
            profile = data[0]
            
            # Also try to get email from auth.users if not in profiles
            if not profile.get("email"):
                # Try to get from auth.users via service role key
                auth_response = self.supabase_service.table("auth.users").select("email").eq("id", user_id).execute()
                if not hasattr(auth_response, 'error') and auth_response.data:
                    profile["email"] = auth_response.data[0].get("email")
            
            # Ensure we have the required fields for digest
            user_data = {
                "id": profile.get("id"),
                "email": profile.get("email", "user@example.com"),  # Fallback
                "first_name": profile.get("nickname") or profile.get("username") or "User",  # Use nickname as first name
                "nickname": profile.get("nickname"),
                "username": profile.get("username"),
                "avatar_url": profile.get("avatar_url"),
                "created_at": profile.get("created_at"),
                "updated_at": profile.get("updated_at")
            }
            
            logger.info(f"Retrieved user profile data for {user_id}")
            return user_data
            
        except Exception as e:
            logger.error(f"Error fetching user profile data for {user_id}: {e}")
            return None

        