-- Sub-Zero Enterprise Schema Migration
-- Run this in Supabase SQL Editor
-- WARNING: This will drop and recreate tables with enterprise schema

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- DROP CONFLICTING TABLES (in correct order due to foreign keys)
-- ============================================================================

-- Drop views first
DROP VIEW IF EXISTS subscription_health CASCADE;
DROP VIEW IF EXISTS tool_dependency_impact CASCADE;

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS notification_preferences CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS org_sync_history CASCADE;
DROP TABLE IF EXISTS org_integrations CASCADE;
DROP TABLE IF EXISTS escalations CASCADE;
DROP TABLE IF EXISTS decisions CASCADE;
DROP TABLE IF EXISTS integration_catalog CASCADE;
DROP TABLE IF EXISTS tool_dependencies CASCADE;
DROP TABLE IF EXISTS usage_daily_agg CASCADE;
DROP TABLE IF EXISTS usage_signals CASCADE;
DROP TABLE IF EXISTS tool_access CASCADE;
DROP TABLE IF EXISTS tool_subscriptions CASCADE;
DROP TABLE IF EXISTS saas_tools CASCADE;
DROP TABLE IF EXISTS org_users CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Organizations (tenants)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    domain TEXT UNIQUE NOT NULL,
    plan TEXT DEFAULT 'trial',
    settings JSONB DEFAULT '{}',
    sso_provider TEXT,
    sso_config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users (employees in the organization)
CREATE TABLE org_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT,
    avatar_url TEXT,
    department TEXT,
    job_title TEXT,
    role TEXT DEFAULT 'member',
    manager_id UUID REFERENCES org_users(id),
    status TEXT DEFAULT 'active',
    sso_provider TEXT,
    sso_id TEXT,
    last_login_at TIMESTAMPTZ,
    offboarded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, email)
);

-- SaaS Tools catalog
CREATE TABLE saas_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    category TEXT,
    vendor_domain TEXT,
    vendor_url TEXT,
    logo_url TEXT,
    description TEXT,
    discovery_source TEXT,
    discovery_data JSONB,
    status TEXT DEFAULT 'active',
    is_keystone BOOLEAN DEFAULT FALSE,
    keystone_score FLOAT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, normalized_name)
);

-- Subscriptions (billing info)
CREATE TABLE tool_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES saas_tools(id) ON DELETE CASCADE,
    plan_name TEXT,
    billing_cycle TEXT,
    amount_cents INTEGER,
    currency TEXT DEFAULT 'USD',
    paid_seats INTEGER,
    active_seats INTEGER DEFAULT 0,
    renewal_date DATE,
    contract_start_date DATE,
    contract_end_date DATE,
    auto_renew BOOLEAN DEFAULT TRUE,
    cancellation_notice_days INTEGER DEFAULT 30,
    owner_id UUID REFERENCES org_users(id),
    department TEXT,
    cost_center TEXT,
    purchase_order TEXT,
    notes TEXT,
    status TEXT DEFAULT 'active',
    billing_source TEXT,
    billing_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tool Access (who has access to what)
CREATE TABLE tool_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES saas_tools(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES org_users(id) ON DELETE CASCADE,
    access_level TEXT DEFAULT 'user',
    license_type TEXT,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by UUID REFERENCES org_users(id),
    last_active_at TIMESTAMPTZ,
    activity_days_30 INTEGER DEFAULT 0,
    activity_days_90 INTEGER DEFAULT 0,
    activity_score FLOAT DEFAULT 0,
    status TEXT DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    UNIQUE(tool_id, user_id)
);

-- ============================================================================
-- USAGE & SIGNALS
-- ============================================================================

-- Usage Signals (privacy-safe activity tracking)
CREATE TABLE usage_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES saas_tools(id) ON DELETE CASCADE,
    user_id UUID REFERENCES org_users(id),
    signal_type TEXT NOT NULL,
    signal_date DATE NOT NULL,
    count INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily aggregated usage (for fast queries)
CREATE TABLE usage_daily_agg (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    tool_id UUID NOT NULL REFERENCES saas_tools(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    active_users INTEGER DEFAULT 0,
    total_logins INTEGER DEFAULT 0,
    total_api_calls INTEGER DEFAULT 0,
    UNIQUE(tool_id, date)
);

-- ============================================================================
-- GRAPH: DEPENDENCIES
-- ============================================================================

-- Tool Dependencies (graph edges)
CREATE TABLE tool_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_tool_id UUID NOT NULL REFERENCES saas_tools(id) ON DELETE CASCADE,
    target_tool_id UUID NOT NULL REFERENCES saas_tools(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL,
    strength FLOAT DEFAULT 0.5,
    direction TEXT DEFAULT 'outgoing',
    description TEXT,
    auto_discovered BOOLEAN DEFAULT FALSE,
    verified BOOLEAN DEFAULT FALSE,
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_tool_id, target_tool_id, dependency_type)
);

-- Known integrations catalog (system-wide)
CREATE TABLE integration_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_tool_name TEXT NOT NULL,
    target_tool_name TEXT NOT NULL,
    integration_type TEXT NOT NULL,
    default_strength FLOAT DEFAULT 0.5,
    description TEXT,
    UNIQUE(source_tool_name, target_tool_name, integration_type)
);

-- ============================================================================
-- DECISIONS & ACTIONS
-- ============================================================================

-- Decisions
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES tool_subscriptions(id) ON DELETE CASCADE,
    tool_id UUID REFERENCES saas_tools(id) ON DELETE CASCADE,
    decision_type TEXT NOT NULL,
    reason TEXT,
    confidence FLOAT,
    risk_score FLOAT,
    risk_factors JSONB,
    savings_potential_cents INTEGER DEFAULT 0,
    current_seats INTEGER,
    recommended_seats INTEGER,
    factors JSONB,
    explanation TEXT,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'normal',
    due_date DATE,
    decided_by UUID REFERENCES org_users(id),
    decided_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    execution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Escalations
CREATE TABLE escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    decision_id UUID NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    level INTEGER DEFAULT 1,
    channel TEXT NOT NULL,
    recipient_id UUID REFERENCES org_users(id),
    recipient_email TEXT,
    recipient_phone TEXT,
    subject TEXT,
    message TEXT,
    template_id TEXT,
    scheduled_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,
    response_type TEXT,
    response_data JSONB,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INTEGRATIONS
-- ============================================================================

-- Connected integrations
CREATE TABLE org_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    scopes TEXT[],
    last_sync_at TIMESTAMPTZ,
    sync_status TEXT,
    sync_error TEXT,
    config JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    connected_by UUID REFERENCES org_users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, provider)
);

-- Sync history
CREATE TABLE org_sync_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    integration_id UUID REFERENCES org_integrations(id) ON DELETE CASCADE,
    sync_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    records_processed INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    errors JSONB,
    metadata JSONB
);

-- ============================================================================
-- AUDIT & COMPLIANCE
-- ============================================================================

-- Audit Log
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES org_users(id),
    actor_email TEXT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    entity_name TEXT,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- NOTIFICATIONS & PREFERENCES
-- ============================================================================

-- Notification preferences
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES org_users(id),
    channel TEXT NOT NULL,
    event_type TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    UNIQUE(user_id, channel, event_type)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Organizations
CREATE INDEX idx_organizations_domain ON organizations(domain);

-- Users
CREATE INDEX idx_org_users_org ON org_users(org_id);
CREATE INDEX idx_org_users_email ON org_users(email);
CREATE INDEX idx_org_users_status ON org_users(org_id, status);
CREATE INDEX idx_org_users_manager ON org_users(manager_id);

-- Tools
CREATE INDEX idx_saas_tools_org ON saas_tools(org_id);
CREATE INDEX idx_saas_tools_category ON saas_tools(org_id, category);
CREATE INDEX idx_saas_tools_status ON saas_tools(org_id, status);

-- Subscriptions
CREATE INDEX idx_tool_subscriptions_org ON tool_subscriptions(org_id);
CREATE INDEX idx_tool_subscriptions_tool ON tool_subscriptions(tool_id);
CREATE INDEX idx_tool_subscriptions_renewal ON tool_subscriptions(renewal_date);
CREATE INDEX idx_tool_subscriptions_owner ON tool_subscriptions(owner_id);
CREATE INDEX idx_tool_subscriptions_status ON tool_subscriptions(org_id, status);

-- Access
CREATE INDEX idx_tool_access_org ON tool_access(org_id);
CREATE INDEX idx_tool_access_user ON tool_access(user_id);
CREATE INDEX idx_tool_access_tool ON tool_access(tool_id);
CREATE INDEX idx_tool_access_active ON tool_access(tool_id, last_active_at);

-- Usage
CREATE INDEX idx_usage_signals_tool_date ON usage_signals(tool_id, signal_date);
CREATE INDEX idx_usage_signals_user ON usage_signals(user_id, signal_date);
CREATE INDEX idx_usage_daily_tool ON usage_daily_agg(tool_id, date);

-- Dependencies
CREATE INDEX idx_tool_deps_source ON tool_dependencies(source_tool_id);
CREATE INDEX idx_tool_deps_target ON tool_dependencies(target_tool_id);

-- Decisions
CREATE INDEX idx_decisions_org ON decisions(org_id);
CREATE INDEX idx_decisions_status ON decisions(org_id, status);
CREATE INDEX idx_decisions_subscription ON decisions(subscription_id);

-- Escalations
CREATE INDEX idx_escalations_decision ON escalations(decision_id);
CREATE INDEX idx_escalations_status ON escalations(status);

-- Audit
CREATE INDEX idx_audit_org ON audit_log(org_id);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Apply to tables
DROP TRIGGER IF EXISTS update_organizations_updated_at ON organizations;
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_org_users_updated_at ON org_users;
CREATE TRIGGER update_org_users_updated_at BEFORE UPDATE ON org_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_saas_tools_updated_at ON saas_tools;
CREATE TRIGGER update_saas_tools_updated_at BEFORE UPDATE ON saas_tools
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_tool_subscriptions_updated_at ON tool_subscriptions;
CREATE TRIGGER update_tool_subscriptions_updated_at BEFORE UPDATE ON tool_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_decisions_updated_at ON decisions;
CREATE TRIGGER update_decisions_updated_at BEFORE UPDATE ON decisions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_org_integrations_updated_at ON org_integrations;
CREATE TRIGGER update_org_integrations_updated_at BEFORE UPDATE ON org_integrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Tool dependency impact view
CREATE OR REPLACE VIEW tool_dependency_impact AS
WITH RECURSIVE dependency_chain AS (
    SELECT
        td.target_tool_id as root_tool_id,
        td.source_tool_id as dependent_tool_id,
        td.dependency_type,
        td.strength,
        1 as depth,
        ARRAY[td.source_tool_id] as path
    FROM tool_dependencies td

    UNION ALL

    SELECT
        dc.root_tool_id,
        td.source_tool_id,
        td.dependency_type,
        td.strength,
        dc.depth + 1,
        dc.path || td.source_tool_id
    FROM tool_dependencies td
    JOIN dependency_chain dc ON td.target_tool_id = dc.dependent_tool_id
    WHERE td.source_tool_id != ALL(dc.path)
    AND dc.depth < 5
)
SELECT
    root_tool_id as tool_id,
    COUNT(DISTINCT dependent_tool_id) as total_dependents,
    MAX(depth) as max_depth,
    AVG(strength) as avg_strength
FROM dependency_chain
GROUP BY root_tool_id;

-- Subscription health view
CREATE OR REPLACE VIEW subscription_health AS
SELECT
    s.id as subscription_id,
    s.org_id,
    s.tool_id,
    t.name as tool_name,
    s.paid_seats,
    COALESCE(s.active_seats, 0) as active_seats,
    CASE WHEN s.paid_seats > 0
        THEN ROUND(COALESCE(s.active_seats, 0)::numeric / s.paid_seats, 2)
        ELSE 0
    END as utilization_rate,
    s.amount_cents,
    s.renewal_date,
    s.renewal_date - CURRENT_DATE as days_until_renewal,
    s.auto_renew,
    s.owner_id,
    u.name as owner_name,
    u.status as owner_status,
    COALESCE(di.total_dependents, 0) as dependent_tools,
    CASE
        WHEN s.renewal_date <= CURRENT_DATE + 7 THEN 'urgent'
        WHEN s.renewal_date <= CURRENT_DATE + 30 THEN 'soon'
        WHEN s.renewal_date <= CURRENT_DATE + 60 THEN 'upcoming'
        ELSE 'ok'
    END as renewal_urgency
FROM tool_subscriptions s
JOIN saas_tools t ON s.tool_id = t.id
LEFT JOIN org_users u ON s.owner_id = u.id
LEFT JOIN tool_dependency_impact di ON s.tool_id = di.tool_id
WHERE s.status = 'active';




-- ============================================================================
-- DONE
-- ============================================================================
SELECT 'Enterprise schema migration complete!' as status;
