"""
Timezone utilities for consistent datetime handling across the application.
"""
from datetime import datetime, timezone
from typing import Optional

def to_utc(dt) -> Optional[datetime]:
    """
    Return a timezone-aware UTC datetime (or None). Accepts str or datetime.
    
    Args:
        dt: String datetime or datetime object
        
    Returns:
        Timezone-aware UTC datetime or None if parsing fails
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        # tolerant ISO parsing incl. trailing 'Z'
        s = dt.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(s)
        except Exception:
            return None
        dt = parsed
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt

def now_utc() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)
