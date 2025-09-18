-- Email system database schema
-- Run this migration to add email functionality to your Supabase database

-- 1) Email preferences (one row per user)
CREATE TABLE IF NOT EXISTS email_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    weekly_digest_enabled BOOLEAN NOT NULL DEFAULT true,
    preferred_day INT NOT NULL DEFAULT 1,        -- 0=Sun..6=Sat; 1=Monday (ISO)
    preferred_hour INT NOT NULL DEFAULT 9,       -- 0..23 local hour
    timezone TEXT NOT NULL DEFAULT 'America/Los_Angeles',
    no_activity_policy TEXT NOT NULL DEFAULT 'skip', -- 'skip' | 'brief' | 'suggestions'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CHECK (preferred_day >= 0 AND preferred_day <= 6),
    CHECK (preferred_hour >= 0 AND preferred_hour <= 23),
    CHECK (no_activity_policy IN ('skip', 'brief', 'suggestions'))
);

-- 2) Digest send history (idempotency + audit)
CREATE TABLE IF NOT EXISTS email_digests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,                    -- normalized to Monday (or your chosen week start)
    status TEXT NOT NULL CHECK (status IN ('queued','rendered','sent','failed')),
    message_id TEXT,                             -- Brevo message id
    error TEXT,
    retry_count INT NOT NULL DEFAULT 0,
    payload JSONB,                               -- stored rendered snapshot (subject/body variables)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Idempotency guard - prevents duplicate sends
    UNIQUE (user_id, week_start)
);

-- 3) Unsubscribe tokens (for secure unsubscribe links)
CREATE TABLE IF NOT EXISTS unsubscribe_tokens (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4) Email events from Brevo webhooks (deliverability analytics)
CREATE TABLE IF NOT EXISTS email_events (
    id BIGSERIAL PRIMARY KEY,
    message_id TEXT,
    event TEXT NOT NULL,                         -- delivered, opened, clicked, bounced, spam, unsub
    user_id UUID,                                -- backfilled via join on email_digests.message_id
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    meta JSONB
);

-- 5) Suppression list (hard bounces, complaints, unsubscribes)
CREATE TABLE IF NOT EXISTS email_suppressions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('bounce', 'complaint', 'unsubscribe', 'manual')),
    message_id TEXT,                             -- Brevo message id that caused suppression
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure unique suppressions per email
    UNIQUE (email, reason)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_email_digests_user_week ON email_digests(user_id, week_start);
CREATE INDEX IF NOT EXISTS idx_email_digests_status ON email_digests(status);
CREATE INDEX IF NOT EXISTS idx_email_digests_created ON email_digests(created_at);
CREATE INDEX IF NOT EXISTS idx_email_events_message_id ON email_events(message_id);
CREATE INDEX IF NOT EXISTS idx_email_events_user_id ON email_events(user_id);
CREATE INDEX IF NOT EXISTS idx_email_events_occurred ON email_events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_email_suppressions_email ON email_suppressions(email);
CREATE INDEX IF NOT EXISTS idx_unsubscribe_tokens_token ON unsubscribe_tokens(token);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_email_preferences_updated_at 
    BEFORE UPDATE ON email_preferences 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_digests_updated_at 
    BEFORE UPDATE ON email_digests 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS (Row Level Security) policies
ALTER TABLE email_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_digests ENABLE ROW LEVEL SECURITY;
ALTER TABLE unsubscribe_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_suppressions ENABLE ROW LEVEL SECURITY;

-- Users can only access their own email data
CREATE POLICY "Users can view own email preferences" ON email_preferences
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own email preferences" ON email_preferences
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own email preferences" ON email_preferences
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own email digests" ON email_digests
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own unsubscribe tokens" ON unsubscribe_tokens
    FOR SELECT USING (auth.uid() = user_id);

-- Service role can access all email data (for cron jobs)
CREATE POLICY "Service role can access all email data" ON email_preferences
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all email digests" ON email_digests
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all unsubscribe tokens" ON unsubscribe_tokens
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all email events" ON email_events
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can access all suppressions" ON email_suppressions
    FOR ALL USING (auth.role() = 'service_role');

-- Initialize email preferences for existing users
INSERT INTO email_preferences (user_id, weekly_digest_enabled, preferred_day, preferred_hour, timezone, no_activity_policy)
SELECT 
    id as user_id,
    true as weekly_digest_enabled,
    1 as preferred_day,
    9 as preferred_hour,
    'America/Los_Angeles' as timezone,
    'skip' as no_activity_policy
FROM auth.users
WHERE id NOT IN (SELECT user_id FROM email_preferences)
ON CONFLICT (user_id) DO NOTHING;

