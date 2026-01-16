-- Sub-Zero Database Schema
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- data_sources table (OAuth connections)
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    sync_in_progress BOOLEAN DEFAULT FALSE,
    sync_started_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- processed_emails table (track already processed emails to avoid duplicates)
CREATE TABLE processed_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    message_id TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, message_id)
);
CREATE INDEX idx_processed_emails_user ON processed_emails(user_id);

-- subscriptions table
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    vendor_name TEXT NOT NULL,
    vendor_normalized TEXT,
    amount_cents INTEGER,
    currency TEXT DEFAULT 'USD',
    billing_cycle TEXT,
    last_charge_at TIMESTAMPTZ,
    next_renewal_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active',
    source TEXT DEFAULT 'gmail',
    confidence FLOAT DEFAULT 1.0,
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- usage_signals table
CREATE TABLE usage_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE CASCADE,
    signal_type TEXT NOT NULL,
    signal_value JSONB,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- decisions table
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE CASCADE,
    decision_type TEXT NOT NULL,
    reason TEXT,
    confidence FLOAT,
    user_action TEXT,
    acted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_vendor ON subscriptions(vendor_normalized);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_decisions_user_pending ON decisions(user_id) WHERE user_action IS NULL;
CREATE INDEX idx_usage_signals_sub ON usage_signals(subscription_id);
CREATE INDEX idx_data_sources_user ON data_sources(user_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for subscriptions updated_at
CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (optional, enable if using Supabase Auth directly)
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE usage_signals ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
