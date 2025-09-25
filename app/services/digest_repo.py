"""
Database repository for digest system.
Handles all database operations for email preferences, digests, and user activity.
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from supabase import create_client, Client
import os
from ..utils.timezone_utils import now_utc

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
            # First get email preferences (use service role to bypass RLS)
            prefs_response = self.supabase_service.table("email_preferences").select(
                "user_id, weekly_digest_enabled, preferred_day, preferred_hour, timezone, no_activity_policy"
            ).eq("weekly_digest_enabled", True).execute()
            
            if hasattr(prefs_response, 'error') and prefs_response.error:
                logger.error(f"Error fetching email preferences: {prefs_response.error}")
                return []
            
            if not prefs_response.data:
                logger.info("No users with weekly_digest_enabled=True found")
                return []
            
            logger.info(f"Found {len(prefs_response.data)} users with weekly_digest_enabled=True")
            
            users = []
            for pref in prefs_response.data:
                user_id = pref.get("user_id")
                if not user_id:
                    logger.warning(f"⚠️ DIGEST REPO: No user_id found in preference: {pref}")
                    continue
                
                # Get user email from profiles table (extract from username)
                # This is simpler and more reliable than accessing auth.users
                user_email = None
                
                # Get user profile data and extract email from username
                try:
                    profile_response = self.supabase_service.table("profiles").select(
                        "id, nickname, username, avatar_url, bio, created_at, updated_at"
                    ).eq("id", user_id).execute()
                    
                    profile_data = profile_response.data[0] if profile_response.data else {}
                    
                    # Extract email from username (first half before _) + @gmail.com
                    if profile_data and profile_data.get("username"):
                        username = profile_data["username"]
                        email_prefix = username.split("_")[0]
                        user_email = f"{email_prefix}@gmail.com"
                        logger.info(f"✅ Extracted email for user {user_id}: {user_email} (from username: {username})")
                    else:
                        logger.warning(f"No username found for user {user_id} in profiles")
                        continue
                        
                except Exception as e:
                    logger.warning(f"Could not fetch profile for user {user_id}: {e}")
                    continue
                
                users.append({
                    "id": user_id,
                    "email": user_email,
                    "first_name": profile_data.get("nickname") or profile_data.get("username", "").split("_")[0],
                    "name": profile_data.get("nickname") or profile_data.get("username", ""),
                    "timezone": pref["timezone"],
                    "preferred_day": pref["preferred_day"],
                    "preferred_hour": pref["preferred_hour"],
                    "no_activity_policy": pref["no_activity_policy"],
                    "created_at": profile_data.get("created_at"),
                    "profile_id": profile_data.get("id")  # Include profile id for reference
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
            # Get ALL insights first (no SQL date filtering), then filter in Python
            # This matches the pattern used by ai_summary_service.py for consistency
            insights_response = self.supabase_service.table("insights").select(
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
            ).eq("user_id", user_id).order("created_at", desc=True).execute()
            
            if hasattr(insights_response, 'error') and insights_response.error:
                logger.error(f"Error fetching insights for user {user_id}: {insights_response.error}")
                insights = []
            else:
                all_insights = insights_response.data or []
                logger.info(f"DIGEST REPO: Retrieved {len(all_insights)} total insights for user {user_id}")
                
                # Filter in Python: include items created OR updated within window
                def _parse_dt(s: str) -> datetime:
                    # Handle "Z" and timezone-aware strings robustly
                    if not s:
                        return None
                    try:
                        # Normalize trailing 'Z'
                        if s.endswith("Z"):
                            s = s[:-1] + "+00:00"
                        return datetime.fromisoformat(s)
                    except Exception:
                        return None
                
                insights = []
                for insight in all_insights:
                    created_dt = _parse_dt(insight.get("created_at"))
                    updated_dt = _parse_dt(insight.get("updated_at"))
                    
                    # Include if created OR updated within the time window
                    if created_dt and start_utc <= created_dt < end_utc:
                        insights.append(insight)
                    elif updated_dt and start_utc <= updated_dt < end_utc:
                        insights.append(insight)
                
                logger.info(f"DIGEST REPO: Filtered to {len(insights)} insights in date range {start_utc.isoformat()} to {end_utc.isoformat()}")
            
            # Get ALL stacks first, then filter in Python (same pattern as insights)
            stacks_response = self.supabase_service.table("stacks").select(
                """
                id,
                name,
                description,
                created_at,
                updated_at
                """
            ).eq("user_id", user_id).order("created_at", desc=True).execute()
            
            if hasattr(stacks_response, 'error') and stacks_response.error:
                logger.error(f"Error fetching stacks for user {user_id}: {stacks_response.error}")
                stacks = []
            else:
                all_stacks = stacks_response.data or []
                logger.info(f"DIGEST REPO: Retrieved {len(all_stacks)} total stacks for user {user_id}")
                
                # Filter stacks in Python using the same date filtering logic
                stacks = []
                for stack in all_stacks:
                    created_dt = _parse_dt(stack.get("created_at"))
                    updated_dt = _parse_dt(stack.get("updated_at"))
                    
                    # Include if created OR updated within the time window
                    if created_dt and start_utc <= created_dt < end_utc:
                        stacks.append(stack)
                    elif updated_dt and start_utc <= updated_dt < end_utc:
                        stacks.append(stack)
                
                logger.info(f"DIGEST REPO: Filtered to {len(stacks)} stacks in date range")
            
            # Get stack item counts
            for stack in stacks:
                stack_id = stack["id"]
                items_response = self.supabase_service.table("insights").select("id").eq("stack_id", stack_id).execute()
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
            logger.info(f"🔍 Checking for existing digest: user {user_id}, week {week_start}")
            response = self.supabase_service.table("email_digests").select("*") \
                .eq("user_id", user_id) \
                .eq("week_start", week_start.isoformat()) \
                .limit(1) \
                .execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"❌ Error fetching digest for user {user_id}, week {week_start}: {response.error}")
                return None
            
            data = response.data or []
            if data:
                digest_info = data[0]
                logger.info(f"✅ Found existing digest for user {user_id}, week {week_start}: ID={digest_info['id']}, status={digest_info['status']}, created={digest_info.get('created_at', 'unknown')}")
                return digest_info
            else:
                logger.info(f"ℹ️ No existing digest found for user {user_id}, week {week_start}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching digest for user {user_id}, week {week_start}: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return None
    
    async def create_digest_record(
        self, 
        user_id: str, 
        week_start: datetime.date, 
        status: str
    ) -> str:
        """
        Create a new digest record using atomic upsert.
        
        Args:
            user_id: User ID
            week_start: Week start date
            status: Initial status
        
        Returns:
            Digest record ID
        """
        payload = {
            "user_id": user_id,
            "week_start": week_start.isoformat(),
            "status": status,
            "retry_count": 0
        }
        resp = self.supabase_service.table("email_digests") \
            .upsert(payload, on_conflict=["user_id", "week_start"]) \
            .execute()
        if hasattr(resp, "error") and resp.error:
            raise Exception(f"Failed to upsert digest record: {resp.error}")
        if resp.data and len(resp.data) > 0:
            logger.info(f"✅ Upserted digest record {resp.data[0]['id']} for user {user_id}, week {week_start}")
            return resp.data[0]["id"]
        existing = await self.get_digest_by_user_week(user_id, week_start)
        if not existing:
            raise Exception("Upsert succeeded but could not fetch digest record")
        logger.info(f"✅ Found existing digest record {existing['id']} for user {user_id}, week {week_start}")
        return existing["id"]
    
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
                "updated_at": now_utc().isoformat()
            }
            
            if message_id is not None:
                update_data["message_id"] = message_id
            
            if error is not None:
                update_data["error"] = error
                # increment server-side; don't assign RPC response into the row
                rpc_resp = self.supabase_service.rpc("increment_retry_count", {"digest_id": digest_id}).execute()
                if hasattr(rpc_resp, "error") and rpc_resp.error:
                    logger.warning(f"increment_retry_count failed: {rpc_resp.error}")
            
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
            
            # Ensure user_id is included in the result
            if result:
                result["user_id"] = user_id
                logger.info(f"🔐 DIGEST REPO: Added user_id to preferences: {result}")
            
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
                "preferred_day": 6,  # Saturday
                "preferred_hour": 20,  # 8 PM
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
            response = self.supabase_service.table("email_preferences") \
                .update({"weekly_digest_enabled": False}) \
                .eq("user_id", user_id).execute()
            
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
                "occurred_at": now_utc().isoformat()
            }
            
            if user_id:
                event_data["user_id"] = user_id
            
            if meta:
                event_data["meta"] = meta
            
            response = self.supabase_service.table("email_events").insert(event_data).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error logging email event: {response.error}")
                return False
            
            logger.info(f"Logged email event: {event} for message {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging email event: {e}")
            return False
    
    # Note: log_digest_sent function removed - email_digests table is redundant
    # All digest information is now tracked in email_events table with proper event types
    
    async def get_digest_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get digest statistics for the last N days using email_events table.
        
        Args:
            days: Number of days to look back
        
        Returns:
            Statistics dictionary
        """
        try:
            from datetime import timedelta, timezone
            cutoff_date = (now_utc() - timedelta(days=days)).isoformat()
            
            # Get email events for the period
            response = self.supabase_service.table("email_events").select("*").gte("occurred_at", cutoff_date).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error fetching email events stats: {response.error}")
                return {}
            
            events = response.data or []
            
            # Count events by type
            event_counts = {}
            sent_emails = set()  # Track unique message_ids for sent emails
            
            for event in events:
                event_type = event.get("event", "unknown")
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
                
                if event_type == "sent":
                    sent_emails.add(event.get("message_id"))
            
            # Get total users with preferences
            prefs_response = self.supabase_service.table("email_preferences").select("user_id").eq("weekly_digest_enabled", True).execute()
            total_users = len(prefs_response.data or []) if not hasattr(prefs_response, 'error') else 0
            
            return {
                "total_users": total_users,
                "emails_sent": len(sent_emails),
                "emails_delivered": event_counts.get("delivered", 0),
                "emails_opened": event_counts.get("opened", 0),
                "emails_bounced": event_counts.get("bounced", 0),
                "emails_spam": event_counts.get("spam", 0),
                "total_events": len(events),
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error fetching email events stats: {e}")
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
                username,
                avatar_url,
                bio,
                created_at,
                updated_at,
                memory_profile,
                is_admin
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
            
            # Get email from auth.users since it's not in profiles table
            try:
                auth_response = self.supabase_service.table("auth.users").select("email").eq("id", user_id).execute()
                if not hasattr(auth_response, 'error') and auth_response.data:
                    profile["email"] = auth_response.data[0].get("email")
                else:
                    profile["email"] = "user@example.com"  # Fallback
            except Exception as e:
                logger.warning(f"Could not fetch email from auth.users for {user_id}: {e}")
                profile["email"] = "user@example.com"  # Fallback
            
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

    async def get_recent_insights(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get recent insights for a user within the specified number of days.
        
        Args:
            user_id: User ID
            days: Number of days to look back
        
        Returns:
            List of insights (empty list if none found)
        """
        try:
            from datetime import datetime, timezone, timedelta
            
            # 1) Compute window in UTC
            now_utc = datetime.now(timezone.utc)
            start_utc = now_utc - timedelta(days=days)
            
            logger.info(f"📧 EMAIL DIGEST: Fetching insights for user {user_id} from {start_utc.isoformat()} to {now_utc.isoformat()}")
            
            # 2) Use the same SELECT signature as insights_service.py (WORKING PATTERN)
            # *** FIX: Use SERVICE CLIENT to bypass RLS for server-side email digest reads ***
            query = self.supabase_service.table("insights").select(
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
            ).eq("user_id", user_id).order("created_at", desc=True)
            
            # 3) Execute without SQL date filters (mirrors working MySpace pattern)
            resp = query.execute()
            if hasattr(resp, "error") and resp.error:
                logger.error(f"📧 EMAIL DIGEST: Error fetching insights for user {user_id}: {resp.error}")
                return []
            
            rows = resp.data or []
            logger.info(f"📧 EMAIL DIGEST: Retrieved {len(rows)} total insights for user {user_id}")
            
            # Sanity check for RLS/identity issues
            if not rows:
                logger.warning(
                    f"📧 EMAIL DIGEST: No insights returned for user {user_id}. "
                    f"Using service client to bypass RLS. Check if user has any insights in database."
                )
            
            # 4) Filter in Python: include items created OR updated within window
            def _parse_dt(s: str) -> datetime:
                # Handle "Z" and timezone-aware strings robustly
                if not s:
                    return None
                try:
                    # Normalize trailing 'Z'
                    if s.endswith("Z"):
                        s = s[:-1] + "+00:00"
                    return datetime.fromisoformat(s)
                except Exception:
                    return None
            
            recent = []
            for it in rows:
                c = _parse_dt(it.get("created_at"))
                u = _parse_dt(it.get("updated_at"))
                # Use created_at primarily, fall back to updated_at; count either if within window
                in_window = False
                if c and c >= start_utc:
                    in_window = True
                elif u and u >= start_utc:
                    in_window = True
                if in_window:
                    recent.append(it)
            
            logger.info(f"📧 EMAIL DIGEST: Found {len(recent)} insights for user {user_id} in last {days} days")
            return recent
            
        except Exception as e:
            logger.error(f"Error fetching recent insights for {user_id}: {e}")
            return []

    def summarize_by_tag(self, insights: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Group insights by tags and create summary.
        
        Args:
            insights: List of insight objects
        
        Returns:
            List of {"name": tag_name, "articles": comma_separated_titles}
        """
        try:
            if not insights:
                return []
            
            tags = {}
            for insight in insights:
                insight_tags = insight.get("tags", []) or []
                insight_title = insight.get("title", "Untitled").strip()
                
                if not insight_tags:
                    # Handle untagged insights
                    tags.setdefault("Untagged", []).append(insight_title)
                else:
                    for tag in insight_tags:
                        tag_name = tag if isinstance(tag, str) else tag.get("name", "Untagged")
                        tags.setdefault(tag_name, []).append(insight_title)
            
            result = []
            for tag_name, titles in tags.items():
                # Limit to first 6 titles and join with commas
                article_list = ", ".join(titles[:6])
                result.append({
                    "name": tag_name,
                    "articles": article_list
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error summarizing insights by tag: {e}")
            return []

    async def get_ai_summary(self, insights: List[Dict[str, Any]], user_id: str = None) -> str:
        """
        Generate AI summary of insights using ChatGPT API.
        
        Args:
            insights: List of insight objects
            user_id: User ID for personalized summary (optional)
        
        Returns:
            AI summary string (empty if no insights or generation fails)
        """
        try:
            if not insights:
                return ""
            
            # Import here to avoid circular imports
            from app.services.ai_summary_service import get_ai_summary_service
            
            # Use the new AI summary service if user_id is provided
            if user_id:
                try:
                    ai_service = get_ai_summary_service()
                    
                    # ADD DEBUG LOGGING
                    logger.info(f"AI DEBUG: key={'set' if ai_service.openai_api_key else 'missing'}, "
                               f"client={'init' if ai_service.client else 'none'}, "
                               f"model={ai_service.chat_model}, base={ai_service.openai_base_url}")
                    logger.info(f"AI DEBUG: insights_len={len(insights)} user_id={user_id}")
                    
                    # Check if OpenAI API key is configured
                    if not ai_service.openai_api_key:
                        logger.warning("OpenAI API Key not configured, using fallback summary")
                        return self._get_simple_fallback_summary(insights)
                    
                    # Use asyncio to run the async method
                    import asyncio
                    try:
                        # Try to get the current event loop
                        loop = asyncio.get_running_loop()
                        # If we're in an async context, create a task
                        task = loop.create_task(ai_service.generate_weekly_insights_summary(user_id))
                        # Wait for the task to complete
                        result = await task
                        logger.info(f"AI DEBUG: ChatGPT result length: {len(result) if result else 0}")
                        logger.info(f"AI DEBUG: ChatGPT result preview: {result[:200] if result else 'None'}...")
                        return result
                    except RuntimeError:
                        # No event loop running, create a new one
                        result = asyncio.run(ai_service.generate_weekly_insights_summary(user_id))
                        logger.info(f"AI DEBUG: ChatGPT result length (new loop): {len(result) if result else 0}")
                        logger.info(f"AI DEBUG: ChatGPT result preview (new loop): {result[:200] if result else 'None'}...")
                        return result
                        
                except Exception as e:
                    logger.warning(f"AI summary service failed, using fallback: {e}")
                    import traceback
                    logger.warning(f"AI summary error traceback: {traceback.format_exc()}")
            
            # Fallback to simple summary if AI service fails or user_id not provided
            insight_count = len(insights)
            if insight_count == 1:
                return f"You captured 1 new insight this week. Keep building your knowledge base!"
            else:
                return f"You captured {insight_count} new insights this week. Great job expanding your second brain!"
                
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return ""
    
    def _get_simple_fallback_summary(self, insights: List[Dict[str, Any]]) -> str:
        """Simple fallback summary when AI service is not available"""
        insight_count = len(insights)
        if insight_count == 1:
            return f"You captured 1 new insight this week. Keep building your knowledge base!"
        else:
            return f"You captured {insight_count} new insights this week. Great job expanding your second brain!"

    def get_recommended_content(self, user_id: str) -> tuple[str, str]:
        """
        Get recommended tag and articles for user.
        
        Args:
            user_id: User ID
        
        Returns:
            Tuple of (recommended_tag, recommended_articles)
        """
        try:
            # For now, return placeholder content
            # TODO: Implement actual recommendation logic based on user's interests
            return ("AI & Technology", "3 trending articles in your interests")
            
        except Exception as e:
            logger.error(f"Error getting recommended content for {user_id}: {e}")
            return ("", "")

        