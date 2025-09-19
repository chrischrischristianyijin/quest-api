# Digest Sending Testing Guide

This guide explains how to test the digest sending logic and Brevo integration to ensure everything works correctly.

## Overview

The testing system provides:
- **Decision Logic Testing**: Verify that the schedule/preferences logic correctly determines when to send
- **Dry Run Testing**: Build everything but don't actually send emails
- **Real Send Testing**: Actually send emails via Brevo for verification
- **Unit Tests**: Automated tests for the decision logic

## Quick Start

### 1. Test Decision Logic (No API Required)

```bash
cd /path/to/quest-api
python test_digest_sending.py
```

This will test the decision logic directly without making API calls.

### 2. Test API Endpoints

First, update the test script with your credentials:

```python
# In test_digest_sending.py
API_BASE_URL = "https://your-api-url.com"
TEST_EMAIL = "your-test@example.com"
auth_token = "your-auth-token"
```

Then run the API tests:

```python
# Uncomment the last line in test_digest_sending.py
asyncio.run(test_digest_sending())
```

### 3. Run Unit Tests

```bash
cd /path/to/quest-api
python -m pytest tests/test_email_sender.py -v
```

## API Endpoints

### Test Send Endpoint

**POST** `/api/v1/email/digest/test-send`

Parameters:
- `dry_run` (bool, default: true): If true, build everything but don't call Brevo
- `force` (bool, default: false): If true, ignore schedule and send decision
- `email_override` (string, optional): Send to this email instead of user's email

#### Examples

**1. Dry run - decision only (no send)**
```bash
curl -X POST "https://your-api.com/api/v1/email/digest/test-send?dry_run=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**2. Force dry run (build params but don't send)**
```bash
curl -X POST "https://your-api.com/api/v1/email/digest/test-send?dry_run=true&force=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**3. Real send to test email (force, no schedule wait)**
```bash
curl -X POST "https://your-api.com/api/v1/email/digest/test-send?dry_run=false&force=true&email_override=test@example.com" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**4. Schedule-accurate real send**
```bash
curl -X POST "https://your-api.com/api/v1/email/digest/test-send?dry_run=false" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Response Format

All endpoints return JSON with this structure:

```json
{
  "ok": true,
  "decision": true,
  "forced": false,
  "will_send": true,
  "prefs": {
    "weekly_digest_enabled": true,
    "preferred_day": 2,
    "preferred_hour": 22,
    "timezone": "Asia/Tokyo",
    "no_activity_policy": "skip"
  },
  "stats": {
    "insights_count": 5,
    "has_insights": true
  },
  "mode": "dry_run",
  "email_override": null,
  "current_time_utc": "2025-01-15T13:00:00Z",
  "current_time_local": "2025-01-15T22:00:00+09:00",
  "params_sample": {
    "tags": [{"name": "AI", "articles": "Article 1, Article 2"}],
    "ai_summary": "Your weekly AI summary...",
    "recommended_tag": "Technology",
    "recommended_articles": "Article 3, Article 4"
  },
  "note": "Dry run only. No email sent.",
  "send_result": {
    "success": true,
    "message_id": "brevo-message-id-123",
    "to_email": "test@example.com",
    "sent_at": "2025-01-15T13:00:00Z",
    "template_id": 123
  }
}
```

## Testing Scenarios

### 1. Schedule Testing

Test that emails are sent at the correct time:

1. Set your preferences to a specific day/hour/timezone
2. Wait for the scheduled time
3. Call the endpoint without `force=true`
4. Verify `decision: true` and actual send

### 2. No Activity Policy Testing

Test the "no activity" behavior:

1. Set `no_activity_policy: "skip"`
2. Ensure you have no recent insights
3. Call the endpoint
4. Verify `decision: false` and no send

1. Set `no_activity_policy: "brief"`
2. Ensure you have no recent insights
3. Call the endpoint
4. Verify `decision: true` and send

### 3. Timezone Testing

Test different timezones:

1. Set timezone to "Asia/Tokyo", preferred_day=2, preferred_hour=22
2. Call at 13:00 UTC on Wednesday (22:00 JST)
3. Verify `decision: true`

1. Call at 12:00 UTC on Wednesday (21:00 JST)
2. Verify `decision: false`

### 4. Brevo Integration Testing

Test actual email delivery:

1. Use `force=true` and `email_override=your-email@example.com`
2. Call the endpoint
3. Check your inbox for the email
4. Check Brevo dashboard for delivery status
5. Verify the `message_id` in the response

## Monitoring and Debugging

### Server Logs

Look for these log messages:

```
brevo_send_ok - Email sent successfully
```

### Brevo Dashboard

1. Log into your Brevo account
2. Go to "Statistics" > "Transactional emails"
3. Look for emails with tag "quest-weekly-digest"
4. Check delivery status, opens, clicks, etc.

### Webhook Events (Optional)

Set up Brevo webhooks to track:
- Delivered
- Opened
- Clicked
- Bounced
- Spam

## Common Issues

### 1. "Decision: false" when expected true

- Check timezone settings
- Verify preferred_day matches Python weekday (0=Monday, 6=Sunday)
- Check if `weekly_digest_enabled` is true
- Verify current time matches preferred hour

### 2. "Send failed" errors

- Check `BREVO_API_KEY` environment variable
- Check `BREVO_TEMPLATE_ID` environment variable
- Verify Brevo account is active
- Check email address format

### 3. Template issues

- Ensure template parameters are wrapped under "params" key
- Verify template exists in Brevo
- Check template syntax (Twig)

## Environment Variables

Required for Brevo integration:

```bash
BREVO_API_KEY=your-brevo-api-key
BREVO_TEMPLATE_ID=your-template-id
SENDER_EMAIL=contact@myquestspace.com
SENDER_NAME=Quest
UNSUBSCRIBE_BASE_URL=https://myquestspace.com
```

## Unit Test Examples

```python
def test_should_send_tokyo_time_hit():
    prefs = EmailPrefs(True, 2, 22, "Asia/Tokyo", "skip")
    dt_utc = pytz.UTC.localize(datetime(2025, 9, 10, 13))  # 22:00 JST
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=True) is True

def test_should_skip_no_activity_when_skip():
    prefs = EmailPrefs(True, 2, 22, "Asia/Tokyo", "skip")
    dt_utc = pytz.UTC.localize(datetime(2025, 9, 10, 13))
    assert should_send_weekly_digest(dt_utc, prefs, has_insights=False) is False
```

## Next Steps

1. **Run the tests** to verify everything works
2. **Set up monitoring** to track email delivery
3. **Configure webhooks** for detailed tracking
4. **Test with real users** in a staging environment
5. **Monitor logs** for any issues in production

The testing system gives you complete visibility into the digest sending process, from decision logic to actual delivery via Brevo.
