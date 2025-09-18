"""
Timezone-aware scheduling utilities for weekly digest system.
Handles week boundaries, user timezones, and send timing logic.
"""
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
import pytz
import logging

logger = logging.getLogger(__name__)

def week_start_for(dt: datetime, week_start: int = 1) -> datetime:
    """
    Calculate the start of the week for a given datetime.
    
    Args:
        dt: Input datetime (timezone-aware)
        week_start: Day of week to start on (0=Sunday, 1=Monday, etc.)
    
    Returns:
        Start of week datetime at 00:00:00 in the same timezone
    """
    # Calculate days to subtract to get to week start
    delta = (dt.weekday() - week_start) % 7
    start_date = (dt - timedelta(days=delta)).date()
    return datetime.combine(start_date, datetime.min.time(), tzinfo=dt.tzinfo)

def should_send_now(user_tz: str, preferred_day: int, preferred_hour: int, now_utc: datetime) -> bool:
    """
    Check if it's time to send a digest for a user based on their preferences.
    
    Args:
        user_tz: User's timezone (e.g., 'America/Los_Angeles')
        preferred_day: User's preferred day (0=Sunday, 1=Monday, etc.)
        preferred_hour: User's preferred hour (0-23)
        now_utc: Current UTC time
    
    Returns:
        True if it's time to send, False otherwise
    """
    try:
        tz = pytz.timezone(user_tz)
        now_local = now_utc.astimezone(tz)
        
        # Check if it's the right day and hour
        is_right_day = now_local.weekday() == preferred_day
        is_right_hour = now_local.hour == preferred_hour
        
        # Only send if it's exactly the right time (not past it)
        return is_right_day and is_right_hour
        
    except Exception as e:
        logger.error(f"Error checking send time for timezone {user_tz}: {e}")
        return False

def compute_window(now_utc: datetime, user_tz: str, week_start: int = 1) -> Tuple[datetime, datetime]:
    """
    Compute the time window for the current week's digest.
    
    Args:
        now_utc: Current UTC time
        user_tz: User's timezone
        week_start: Day of week to start on (0=Sunday, 1=Monday, etc.)
    
    Returns:
        Tuple of (week_start_utc, week_end_utc) for the current week
    """
    try:
        tz = pytz.timezone(user_tz)
        now_local = now_utc.astimezone(tz)
        
        # Get week start in user's timezone
        ws_local = week_start_for(now_local, week_start=week_start)
        we_local = ws_local + timedelta(days=7)
        
        # Convert back to UTC
        ws_utc = ws_local.astimezone(pytz.UTC)
        we_utc = we_local.astimezone(pytz.UTC)
        
        return ws_utc, we_utc
        
    except Exception as e:
        logger.error(f"Error computing window for timezone {user_tz}: {e}")
        # Fallback to UTC week
        ws_utc = week_start_for(now_utc, week_start=week_start)
        we_utc = ws_utc + timedelta(days=7)
        return ws_utc, we_utc

def get_user_timezone_offset(user_tz: str, now_utc: datetime) -> int:
    """
    Get the timezone offset in hours for a user's timezone.
    
    Args:
        user_tz: User's timezone
        now_utc: Current UTC time
    
    Returns:
        Offset in hours (positive for east of UTC, negative for west)
    """
    try:
        tz = pytz.timezone(user_tz)
        now_local = now_utc.astimezone(tz)
        offset = now_local.utcoffset()
        return int(offset.total_seconds() / 3600)
    except Exception as e:
        logger.error(f"Error getting timezone offset for {user_tz}: {e}")
        return 0

def batch_users_by_send_time(users: list, now_utc: datetime) -> dict:
    """
    Group users by their next send time for efficient batching.
    
    Args:
        users: List of user dicts with timezone preferences
        now_utc: Current UTC time
    
    Returns:
        Dict mapping (day, hour) -> list of users
    """
    batches = {}
    
    for user in users:
        try:
            tz = pytz.timezone(user['timezone'])
            now_local = now_utc.astimezone(tz)
            
            # Calculate next send time
            preferred_day = user['preferred_day']
            preferred_hour = user['preferred_hour']
            
            # Find next occurrence of preferred day/hour
            days_ahead = (preferred_day - now_local.weekday()) % 7
            if days_ahead == 0 and now_local.hour < preferred_hour:
                # Today, but not yet the preferred hour
                next_send = now_local.replace(hour=preferred_hour, minute=0, second=0, microsecond=0)
            else:
                # Next occurrence
                if days_ahead == 0:
                    days_ahead = 7  # Next week
                next_send = now_local + timedelta(days=days_ahead)
                next_send = next_send.replace(hour=preferred_hour, minute=0, second=0, microsecond=0)
            
            # Convert back to UTC for batching
            next_send_utc = next_send.astimezone(pytz.UTC)
            batch_key = (next_send_utc.weekday(), next_send_utc.hour)
            
            if batch_key not in batches:
                batches[batch_key] = []
            batches[batch_key].append(user)
            
        except Exception as e:
            logger.error(f"Error batching user {user.get('id', 'unknown')}: {e}")
            continue
    
    return batches

def is_weekend(now_utc: datetime, user_tz: str) -> bool:
    """
    Check if it's weekend in the user's timezone.
    
    Args:
        now_utc: Current UTC time
        user_tz: User's timezone
    
    Returns:
        True if it's weekend (Saturday or Sunday)
    """
    try:
        tz = pytz.timezone(user_tz)
        now_local = now_utc.astimezone(tz)
        return now_local.weekday() >= 5  # Saturday = 5, Sunday = 6
    except Exception as e:
        logger.error(f"Error checking weekend for timezone {user_tz}: {e}")
        return False

def get_week_boundaries(now_utc: datetime, user_tz: str, week_start: int = 1) -> dict:
    """
    Get comprehensive week boundary information for a user.
    
    Args:
        now_utc: Current UTC time
        user_tz: User's timezone
        week_start: Day of week to start on
    
    Returns:
        Dict with week boundary information
    """
    try:
        tz = pytz.timezone(user_tz)
        now_local = now_utc.astimezone(tz)
        
        # Current week boundaries
        current_week_start = week_start_for(now_local, week_start)
        current_week_end = current_week_start + timedelta(days=7)
        
        # Previous week boundaries
        prev_week_start = current_week_start - timedelta(days=7)
        prev_week_end = current_week_start
        
        return {
            'current_week_start': current_week_start.astimezone(pytz.UTC),
            'current_week_end': current_week_end.astimezone(pytz.UTC),
            'prev_week_start': prev_week_start.astimezone(pytz.UTC),
            'prev_week_end': prev_week_end.astimezone(pytz.UTC),
            'user_timezone': user_tz,
            'local_time': now_local,
            'is_weekend': is_weekend(now_utc, user_tz)
        }
        
    except Exception as e:
        logger.error(f"Error getting week boundaries for timezone {user_tz}: {e}")
        return {
            'current_week_start': now_utc,
            'current_week_end': now_utc + timedelta(days=7),
            'prev_week_start': now_utc - timedelta(days=7),
            'prev_week_end': now_utc,
            'user_timezone': user_tz,
            'local_time': now_utc,
            'is_weekend': False
        }

