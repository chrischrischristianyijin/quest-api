"""
Unit tests for email sender decision logic.
"""
import pytest
from datetime import datetime
import pytz
from app.services.email_sender import EmailPrefs, should_send_weekly_digest

def _dt(y, m, d, h, tz="UTC"):
    """Helper to create UTC datetime."""
    return pytz.UTC.localize(datetime(y, m, d, h))

def test_should_send_tokyo_time_hit():
    """Test that sending works at the correct Tokyo time."""
    prefs = EmailPrefs(
        weekly_digest_enabled=True,
        preferred_day=2,  # Wednesday
        preferred_hour=22,  # 22:00
        timezone="Asia/Tokyo",
        no_activity_policy="skip"
    )
    # 22:00 JST is 13:00 UTC in winter, 13:00 UTC also around Sep (no DST in Tokyo)
    dt_utc = _dt(2025, 9, 10, 13)  # a Wednesday (2) 13:00 UTC == 22:00 JST
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=True) is True

def test_should_skip_wrong_hour():
    """Test that sending is skipped at wrong hour."""
    prefs = EmailPrefs(True, 2, 22, "Asia/Tokyo", "skip")
    dt_utc = _dt(2025, 9, 10, 12)  # 21:00 JST
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=True) is False

def test_should_skip_wrong_day():
    """Test that sending is skipped on wrong day."""
    prefs = EmailPrefs(True, 2, 22, "Asia/Tokyo", "skip")
    dt_utc = _dt(2025, 9, 9, 13)  # Tuesday 22:00 JST
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=True) is False

def test_should_skip_no_activity_when_skip():
    """Test that sending is skipped when no activity and policy is skip."""
    prefs = EmailPrefs(True, 2, 22, "Asia/Tokyo", "skip")
    dt_utc = _dt(2025, 9, 10, 13)
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=False) is False

def test_should_send_no_activity_when_brief():
    """Test that sending works when no activity but policy is brief."""
    prefs = EmailPrefs(True, 2, 22, "Asia/Tokyo", "brief")
    dt_utc = _dt(2025, 9, 10, 13)
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=False) is True

def test_should_send_no_activity_when_suggestions():
    """Test that sending works when no activity but policy is suggestions."""
    prefs = EmailPrefs(True, 2, 22, "Asia/Tokyo", "suggestions")
    dt_utc = _dt(2025, 9, 10, 13)
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=False) is True

def test_should_skip_when_disabled():
    """Test that sending is skipped when digest is disabled."""
    prefs = EmailPrefs(False, 2, 22, "Asia/Tokyo", "skip")
    dt_utc = _dt(2025, 9, 10, 13)
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=True) is False

def test_should_send_utc_timezone():
    """Test that sending works with UTC timezone."""
    prefs = EmailPrefs(True, 2, 14, "UTC", "skip")  # Wednesday 14:00 UTC
    dt_utc = _dt(2025, 9, 10, 14)  # Wednesday 14:00 UTC
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=True) is True

def test_should_skip_utc_wrong_time():
    """Test that sending is skipped at wrong UTC time."""
    prefs = EmailPrefs(True, 2, 14, "UTC", "skip")
    dt_utc = _dt(2025, 9, 10, 13)  # Wednesday 13:00 UTC
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=True) is False

def test_should_send_est_timezone():
    """Test that sending works with EST timezone."""
    prefs = EmailPrefs(True, 2, 9, "America/New_York", "skip")  # Wednesday 9:00 EST
    # 9:00 EST is 14:00 UTC (assuming standard time)
    dt_utc = _dt(2025, 1, 15, 14)  # Wednesday 14:00 UTC = 9:00 EST
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=True) is True

def test_should_send_edt_timezone():
    """Test that sending works with EDT timezone (daylight saving)."""
    prefs = EmailPrefs(True, 2, 9, "America/New_York", "skip")  # Wednesday 9:00 EDT
    # 9:00 EDT is 13:00 UTC (daylight saving time)
    dt_utc = _dt(2025, 7, 9, 13)  # Wednesday 13:00 UTC = 9:00 EDT
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=True) is True

def test_should_handle_invalid_timezone():
    """Test that invalid timezone defaults to UTC."""
    prefs = EmailPrefs(True, 2, 14, "Invalid/Timezone", "skip")
    dt_utc = _dt(2025, 9, 10, 14)  # Wednesday 14:00 UTC
    # Should work because invalid timezone defaults to UTC
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=True) is True

def test_should_handle_none_timezone():
    """Test that None timezone defaults to UTC."""
    prefs = EmailPrefs(True, 2, 14, None, "skip")
    dt_utc = _dt(2025, 9, 10, 14)  # Wednesday 14:00 UTC
    # Should work because None timezone defaults to UTC
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=True) is True

if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__])
