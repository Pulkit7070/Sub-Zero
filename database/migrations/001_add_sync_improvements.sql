-- Migration: Add sync improvements
-- Run this in Supabase SQL Editor to add incremental sync support

-- Add sync locking columns to data_sources
ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS sync_in_progress BOOLEAN DEFAULT FALSE;
ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS sync_started_at TIMESTAMPTZ;

-- Create processed_emails table to track already-processed emails
CREATE TABLE IF NOT EXISTS processed_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    message_id TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, message_id)
);

-- Create index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_processed_emails_user ON processed_emails(user_id);
