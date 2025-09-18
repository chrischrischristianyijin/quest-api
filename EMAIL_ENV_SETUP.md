# Email Environment Variables Setup

To enable email functionality in the Quest API, add the following environment variables to your `.env` file:

## Required Email Variables

```bash
# Brevo/Sendinblue API Configuration
BREVO_API_KEY=your_brevo_api_key_here  ✅ ADDED TO RENDER
SENDER_EMAIL=contact@myquestspace.com
SENDER_NAME=Quest
UNSUBSCRIBE_BASE_URL=https://myquestspace.com
UNSUBSCRIBE_SECRET_KEY=your_unsubscribe_secret_key_here

# Optional Cron Configuration
CRON_SECRET=your_cron_secret_here
```

## ✅ Current Status
- **BREVO_API_KEY**: ✅ Added to Render deployment
- **Other variables**: Using default values (will work for basic functionality)

## How to Get Brevo API Key

1. Sign up for a Brevo account at https://www.brevo.com/
2. Go to your account settings
3. Navigate to "SMTP & API" section
4. Generate a new API key
5. Copy the key and add it to your `.env` file

## Email Features Enabled

With these environment variables configured, the following email features will be available:

- ✅ Email preferences management (modal)
- ✅ Weekly digest preview
- ✅ Test email sending
- ✅ User unsubscribe functionality
- ✅ Brevo webhook handling
- ✅ Email delivery tracking

## Frontend Integration

The frontend modal (`email-preferences-modal.js`) will automatically:
- Load user preferences from the API
- Save preferences to both API and localStorage
- Send test emails via Brevo
- Preview digest content
- Handle all email-related functionality

## Testing

You can test the email functionality by:
1. Opening the email preferences modal in the frontend
2. Configuring your email settings
3. Sending a test email
4. Previewing the digest content

The modal provides a complete email management interface without requiring page navigation.
