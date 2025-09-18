# Email System Setup Guide

This guide will help you set up the automated weekly email digest system for Quest.

## Overview

The email system includes:
- **Weekly digest emails** with personalized content
- **Timezone-aware scheduling** for global users
- **Idempotent delivery** to prevent duplicates
- **User preferences** and unsubscribe management
- **Deliverability tracking** via Brevo webhooks
- **Preview functionality** for users

## Prerequisites

1. **Brevo Account**: Sign up at [brevo.com](https://brevo.com)
2. **Supabase Database**: Your existing Quest database
3. **Environment Variables**: Configured in your deployment

## Step 1: Database Setup

### Run the Migration

Execute the SQL migration to create the email system tables:

```bash
# Connect to your Supabase database and run:
psql -h your-supabase-host -U postgres -d postgres -f database/migrations/email_system.sql
```

Or use the Supabase dashboard SQL editor to run the migration.

### Verify Tables

Check that these tables were created:
- `email_preferences`
- `email_digests`
- `unsubscribe_tokens`
- `email_events`
- `email_suppressions`

## Step 2: Brevo Configuration

### 1. Create Brevo Account
- Sign up at [brevo.com](https://brevo.com)
- Verify your email address
- Complete account setup

### 2. Get API Key
- Go to Settings → API Keys
- Create a new API key
- Copy the key (starts with `xkeys-`)

### 3. Configure Domain (Optional but Recommended)
- Go to Settings → Senders & IP
- Add your domain (e.g., `quest.example.com`)
- Set up SPF, DKIM, and DMARC records
- Verify domain ownership

### 4. Set Up Webhooks
- Go to Settings → Webhooks
- Create new webhook
- URL: `https://your-api-domain.com/api/v1/email/webhooks/brevo`
- Events: Select all email events (delivered, opened, clicked, bounced, spam, unsubscribed, blocked)

## Step 3: Environment Variables

Add these to your environment configuration:

```bash
# Brevo Configuration
BREVO_API_KEY=xkeys-your-api-key-here
SENDER_EMAIL=no-reply@quest.example.com
SENDER_NAME=Quest
UNSUBSCRIBE_BASE_URL=https://quest.example.com

# Cron Security (for scheduled jobs)
CRON_SECRET=your-secure-random-string-here

# Webhook Security (optional)
WEBHOOK_SECRET=your-webhook-secret-here

# Existing Supabase Configuration
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
```

## Step 4: API Integration

### 1. Add Email Router to Main App

In your main FastAPI app file (`app/main.py` or similar):

```python
from app.api.v1.email import router as email_router

app.include_router(email_router, prefix="/api/v1")
```

### 2. Install Dependencies

Add these to your `requirements.txt`:

```
httpx>=0.24.0
pytz>=2023.3
supabase>=1.0.0
```

### 3. Update API Configuration

Add email endpoints to your API config:

```python
# In your config file
EMAIL: {
    PREFERENCES: '/api/v1/email/preferences',
    PREVIEW: '/api/v1/email/digest/preview',
    UNSUBSCRIBE: '/api/v1/email/unsubscribe',
    TEST: '/api/v1/email/test',
    STATS: '/api/v1/email/stats'
}
```

## Step 5: Frontend Integration

### 1. Add Email Preferences Page

The email preferences page is already created at:
- `src/client/pages/email-preferences.html`
- `src/client/js/email-preferences.js`
- `src/client/styles/email-preferences.css`

### 2. Add Navigation Link

Add a link to email preferences in your navigation:

```html
<a href="email-preferences.html" class="nav-link">Email Preferences</a>
```

### 3. Update API Client

The email preferences JavaScript will automatically use your existing API client.

## Step 6: Scheduling Setup

Choose one of these scheduling options:

### Option 1: Vercel Cron (Recommended for Vercel)

1. Add to `vercel.json`:
```json
{
  "crons": [
    {
      "path": "/api/v1/email/cron/digest",
      "schedule": "0 9 * * 1"
    }
  ]
}
```

2. Set environment variable:
```bash
CRON_SECRET=your-secure-secret
```

### Option 2: GitHub Actions

Create `.github/workflows/digest-cron.yml`:

```yaml
name: Weekly Digest Cron
on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM UTC
  workflow_dispatch:

jobs:
  send-digest:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Digest
        run: |
          curl -X POST \
            -H "X-Cron-Secret: ${{ secrets.CRON_SECRET }}" \
            https://your-api-domain.com/api/v1/email/cron/digest
```

### Option 3: External Cron Service

Use a service like [cron-job.org](https://cron-job.org) to call your endpoint:

- URL: `https://your-api-domain.com/api/v1/email/cron/digest`
- Method: POST
- Headers: `X-Cron-Secret: your-secure-secret`
- Schedule: Every hour (the system will only send to users whose time matches)

## Step 7: Testing

### 1. Test Email Configuration

```bash
curl -X POST \
  -H "Authorization: Bearer your-user-token" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}' \
  https://your-api-domain.com/api/v1/email/test
```

### 2. Test Digest Preview

```bash
curl -X POST \
  -H "Authorization: Bearer your-user-token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "your-user-id"}' \
  https://your-api-domain.com/api/v1/email/digest/preview
```

### 3. Test Cron Job

```bash
curl -X POST \
  -H "X-Cron-Secret: your-secure-secret" \
  https://your-api-domain.com/api/v1/email/cron/digest
```

## Step 8: Monitoring

### 1. Check Email Stats

```bash
curl -H "Authorization: Bearer your-user-token" \
  https://your-api-domain.com/api/v1/email/stats
```

### 2. Monitor Logs

Check your application logs for:
- Digest job execution
- Email sending results
- Webhook processing
- Error messages

### 3. Brevo Dashboard

Monitor in Brevo:
- Email delivery rates
- Bounce rates
- Open and click rates
- Suppression lists

## Troubleshooting

### Common Issues

1. **Emails not sending**
   - Check Brevo API key
   - Verify sender email is configured
   - Check cron job is running
   - Review application logs

2. **Users not receiving emails**
   - Check user preferences are enabled
   - Verify timezone settings
   - Check if user is in suppression list
   - Review digest status in database

3. **Webhook not working**
   - Verify webhook URL is accessible
   - Check webhook secret configuration
   - Review webhook payload format

4. **Database errors**
   - Check Supabase connection
   - Verify table permissions
   - Review RLS policies

### Debug Mode

Enable debug logging by setting:

```python
import logging
logging.getLogger("quest.email").setLevel(logging.DEBUG)
```

## Security Considerations

1. **API Keys**: Store securely, never commit to version control
2. **Cron Secret**: Use a strong, random secret for cron jobs
3. **Webhook Verification**: Implement signature verification for webhooks
4. **Rate Limiting**: Consider rate limiting for email endpoints
5. **Data Privacy**: Ensure user data is handled according to privacy laws

## Performance Optimization

1. **Batch Processing**: The system processes users in batches of 50
2. **Database Indexes**: Ensure proper indexes on frequently queried columns
3. **Caching**: Consider caching user preferences and activity data
4. **Queue System**: For high volume, consider implementing a proper queue system

## Scaling Considerations

- **Brevo Limits**: Free tier allows 300 emails/day
- **Database Performance**: Monitor query performance as user base grows
- **Cron Frequency**: Adjust based on user distribution across timezones
- **Error Handling**: Implement retry logic for failed sends

## Support

For issues or questions:
1. Check the logs first
2. Review this documentation
3. Check Brevo documentation
4. Contact support if needed

## Next Steps

After setup:
1. Test with a small group of users
2. Monitor delivery rates and user feedback
3. Iterate on email content and design
4. Consider A/B testing different send times
5. Add more sophisticated content personalization

