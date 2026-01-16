# Sub-Zero Enterprise: SaaS Governance Platform

## Executive Summary

A company-focused SaaS governance platform that automatically discovers tools, tracks usage, models dependencies, and makes safe cancellation/downsizing decisions.

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SUB-ZERO ENTERPRISE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Frontend   │  │   Backend    │  │   Workers    │  │   AI/Graph   │    │
│  │   (Next.js)  │  │  (FastAPI)   │  │  (Celery)    │  │   Engine     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │             │
│         └─────────────────┴─────────────────┴─────────────────┘             │
│                                   │                                          │
│                        ┌──────────┴──────────┐                              │
│                        │     PostgreSQL      │                              │
│                        │  + pg_graphql/Neo4j │                              │
│                        └─────────────────────┘                              │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                          EXTERNAL INTEGRATIONS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Google    │  │  Microsoft  │  │    Okta     │  │   Billing   │        │
│  │  Workspace  │  │   Entra     │  │    SCIM     │  │   (Stripe)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Slack     │  │    Zoom     │  │   Notion    │  │  100+ SaaS  │        │
│  │    API      │  │    API      │  │    API      │  │    APIs     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | Next.js 14 + Tailwind | Fast, SSR, great DX |
| Backend | FastAPI (Python) | Async, fast, AI-friendly |
| Database | PostgreSQL + Supabase | Proven, scalable, real-time |
| Graph | PostgreSQL JSONB + recursive CTEs | No extra infra |
| Queue | Redis + Celery | Background jobs, scheduling |
| Auth | Supabase Auth + SSO | Enterprise SSO ready |
| Notifications | SendGrid + Twilio | Email + WhatsApp |

---

## 2. Database Schema

### Core Tables

```sql
-- Organizations (tenants)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    domain TEXT UNIQUE NOT NULL,
    plan TEXT DEFAULT 'trial',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users (employees in the organization)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    name TEXT,
    department TEXT,
    role TEXT DEFAULT 'member',  -- admin, finance, it, member
    manager_id UUID REFERENCES users(id),
    status TEXT DEFAULT 'active',  -- active, inactive, offboarded
    sso_provider TEXT,  -- google, microsoft, okta
    sso_id TEXT,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, email)
);

-- SaaS Tools (discovered or manually added)
CREATE TABLE saas_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    category TEXT,  -- productivity, dev-tools, communication, etc.
    vendor_domain TEXT,
    logo_url TEXT,
    discovery_source TEXT,  -- sso, api, billing, manual
    status TEXT DEFAULT 'active',  -- active, deprecated, sunset
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, normalized_name)
);

-- Subscriptions (billing info for tools)
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    tool_id UUID REFERENCES saas_tools(id) ON DELETE CASCADE,
    plan_name TEXT,
    billing_cycle TEXT,  -- monthly, yearly
    amount_cents INTEGER,
    currency TEXT DEFAULT 'USD',
    paid_seats INTEGER,
    renewal_date DATE,
    auto_renew BOOLEAN DEFAULT TRUE,
    contract_end_date DATE,
    owner_id UUID REFERENCES users(id),
    department TEXT,
    cost_center TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tool Access (who has access to what)
CREATE TABLE tool_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    tool_id UUID REFERENCES saas_tools(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    access_level TEXT DEFAULT 'user',  -- admin, user, viewer
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by UUID REFERENCES users(id),
    last_active_at TIMESTAMPTZ,
    activity_score FLOAT DEFAULT 0,  -- 0-1, derived from usage signals
    status TEXT DEFAULT 'active',
    UNIQUE(tool_id, user_id)
);

-- Usage Signals (privacy-safe activity tracking)
CREATE TABLE usage_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    tool_id UUID REFERENCES saas_tools(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    signal_type TEXT NOT NULL,  -- login, api_call, seat_assigned
    signal_date DATE NOT NULL,
    count INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tool Dependencies (graph edges)
CREATE TABLE tool_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    source_tool_id UUID REFERENCES saas_tools(id) ON DELETE CASCADE,
    target_tool_id UUID REFERENCES saas_tools(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL,  -- integration, sso, data_flow, workflow
    strength FLOAT DEFAULT 0.5,  -- 0-1
    description TEXT,
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_tool_id, target_tool_id, dependency_type)
);

-- Decisions (AI/human decisions on subscriptions)
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE CASCADE,
    decision_type TEXT NOT NULL,  -- KEEP, DOWNSIZE, REVIEW, CANCEL
    reason TEXT,
    confidence FLOAT,
    risk_score FLOAT,  -- 0-1, higher = more risky to act
    savings_potential_cents INTEGER,
    recommended_seats INTEGER,  -- for DOWNSIZE
    factors JSONB,  -- explainable factors
    status TEXT DEFAULT 'pending',  -- pending, approved, rejected, executed
    decided_by UUID REFERENCES users(id),
    decided_at TIMESTAMPTZ,
    execute_by DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Escalations (communication workflow)
CREATE TABLE escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    decision_id UUID REFERENCES decisions(id) ON DELETE CASCADE,
    level INTEGER DEFAULT 1,  -- 1=email, 2=reminder, 3=manager, 4=whatsapp
    recipient_id UUID REFERENCES users(id),
    channel TEXT NOT NULL,  -- email, in_app, whatsapp, phone
    message TEXT,
    sent_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,
    response TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Log
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES users(id),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_org ON users(org_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_tools_org ON saas_tools(org_id);
CREATE INDEX idx_subscriptions_org ON subscriptions(org_id);
CREATE INDEX idx_subscriptions_renewal ON subscriptions(renewal_date);
CREATE INDEX idx_tool_access_user ON tool_access(user_id);
CREATE INDEX idx_tool_access_tool ON tool_access(tool_id);
CREATE INDEX idx_usage_signals_tool_date ON usage_signals(tool_id, signal_date);
CREATE INDEX idx_decisions_status ON decisions(status);
CREATE INDEX idx_escalations_status ON escalations(status);
```

---

## 3. Graph Design

### Entity-Relationship Graph

```
                    ┌─────────────┐
                    │ Organization│
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │   User   │    │SaaS Tool │    │Department│
    └────┬─────┘    └────┬─────┘    └──────────┘
         │               │
         │  HAS_ACCESS   │
         └───────┬───────┘
                 │
                 ▼
         ┌──────────────┐
         │ Tool Access  │
         │ (edge data)  │
         └──────────────┘

    Tool ──DEPENDS_ON──▶ Tool
    Tool ──INTEGRATES──▶ Tool
    User ──MANAGES────▶ User
    User ──OWNS───────▶ Subscription
```

### Dependency Types

| Type | Description | Example |
|------|-------------|---------|
| `sso` | Tool uses another for authentication | Notion → Google Workspace |
| `integration` | API/webhook connection | Slack → Jira |
| `data_flow` | Data moves between tools | Salesforce → HubSpot |
| `workflow` | Business process dependency | GitHub → Vercel |
| `embed` | One tool embedded in another | Figma → Notion |

### Graph Queries (PostgreSQL Recursive CTE)

```sql
-- Find all tools dependent on a given tool (impact analysis)
WITH RECURSIVE dependency_chain AS (
    -- Base case: direct dependencies
    SELECT
        source_tool_id,
        target_tool_id,
        dependency_type,
        strength,
        1 as depth,
        ARRAY[source_tool_id] as path
    FROM tool_dependencies
    WHERE target_tool_id = :tool_id

    UNION ALL

    -- Recursive case: indirect dependencies
    SELECT
        td.source_tool_id,
        td.target_tool_id,
        td.dependency_type,
        td.strength,
        dc.depth + 1,
        dc.path || td.source_tool_id
    FROM tool_dependencies td
    JOIN dependency_chain dc ON td.target_tool_id = dc.source_tool_id
    WHERE td.source_tool_id != ALL(dc.path)  -- prevent cycles
    AND dc.depth < 5  -- limit depth
)
SELECT DISTINCT source_tool_id, depth, strength
FROM dependency_chain
ORDER BY depth, strength DESC;

-- Calculate "keystone score" for each tool
SELECT
    t.id,
    t.name,
    COUNT(DISTINCT ta.user_id) as user_count,
    COUNT(DISTINCT td.source_tool_id) as dependent_tools,
    COALESCE(SUM(td.strength), 0) as dependency_strength,
    -- Keystone score: tools that many depend on
    (COUNT(DISTINCT ta.user_id)::float / NULLIF(max_users.total, 0)) * 0.4 +
    (COUNT(DISTINCT td.source_tool_id)::float / NULLIF(max_deps.total, 0)) * 0.6 as keystone_score
FROM saas_tools t
LEFT JOIN tool_access ta ON t.id = ta.tool_id
LEFT JOIN tool_dependencies td ON t.id = td.target_tool_id
CROSS JOIN (SELECT COUNT(*) as total FROM users WHERE org_id = :org_id) max_users
CROSS JOIN (SELECT COUNT(*) as total FROM saas_tools WHERE org_id = :org_id) max_deps
WHERE t.org_id = :org_id
GROUP BY t.id, t.name, max_users.total, max_deps.total
ORDER BY keystone_score DESC;
```

---

## 4. Decision Logic

### Decision Engine (Heuristics-First)

```python
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

class DecisionType(Enum):
    KEEP = "keep"
    DOWNSIZE = "downsize"
    REVIEW = "review"
    CANCEL = "cancel"

@dataclass
class DecisionFactors:
    active_users: int
    paid_seats: int
    utilization_rate: float  # active_users / paid_seats
    last_activity_days: int
    renewal_days: int
    annual_cost: int
    keystone_score: float
    dependency_count: int
    owner_active: bool

@dataclass
class Decision:
    type: DecisionType
    confidence: float
    risk_score: float
    savings_potential: int
    recommended_seats: int | None
    factors: dict
    explanation: str

def make_decision(f: DecisionFactors) -> Decision:
    """
    Conservative decision engine with explainable logic.

    Principles:
    1. Default to KEEP unless strong signal
    2. Never auto-cancel keystone tools
    3. Always explain why
    """

    # Factor weights
    UTILIZATION_WEIGHT = 0.35
    RECENCY_WEIGHT = 0.25
    COST_WEIGHT = 0.20
    DEPENDENCY_WEIGHT = 0.20

    # === RULE 1: Keystone Protection ===
    if f.keystone_score > 0.7:
        return Decision(
            type=DecisionType.KEEP,
            confidence=0.95,
            risk_score=0.9,
            savings_potential=0,
            recommended_seats=None,
            factors={"keystone_score": f.keystone_score},
            explanation=f"Critical tool: {f.dependency_count} tools depend on this"
        )

    # === RULE 2: Owner Departed ===
    if not f.owner_active:
        return Decision(
            type=DecisionType.REVIEW,
            confidence=0.8,
            risk_score=0.5,
            savings_potential=0,
            recommended_seats=None,
            factors={"owner_active": False},
            explanation="Tool owner has left the organization - needs new owner"
        )

    # === RULE 3: Zero Usage ===
    if f.active_users == 0 and f.last_activity_days > 60:
        return Decision(
            type=DecisionType.CANCEL,
            confidence=0.85,
            risk_score=0.2 + (f.keystone_score * 0.3),
            savings_potential=f.annual_cost,
            recommended_seats=None,
            factors={
                "active_users": 0,
                "last_activity_days": f.last_activity_days
            },
            explanation=f"No active users for {f.last_activity_days} days"
        )

    # === RULE 4: Severe Underutilization ===
    if f.utilization_rate < 0.3 and f.paid_seats > 5:
        optimal_seats = max(f.active_users + 2, 5)  # buffer
        savings = ((f.paid_seats - optimal_seats) / f.paid_seats) * f.annual_cost

        return Decision(
            type=DecisionType.DOWNSIZE,
            confidence=0.75,
            risk_score=0.3,
            savings_potential=int(savings),
            recommended_seats=optimal_seats,
            factors={
                "utilization_rate": f.utilization_rate,
                "active_users": f.active_users,
                "paid_seats": f.paid_seats
            },
            explanation=f"Only {f.active_users}/{f.paid_seats} seats used ({f.utilization_rate:.0%})"
        )

    # === RULE 5: Moderate Underutilization ===
    if f.utilization_rate < 0.5:
        return Decision(
            type=DecisionType.REVIEW,
            confidence=0.6,
            risk_score=0.4,
            savings_potential=int(f.annual_cost * 0.3),
            recommended_seats=None,
            factors={
                "utilization_rate": f.utilization_rate,
                "renewal_days": f.renewal_days
            },
            explanation=f"Underutilized ({f.utilization_rate:.0%}) - review before renewal"
        )

    # === RULE 6: Upcoming Renewal Check ===
    if f.renewal_days < 30 and f.utilization_rate < 0.7:
        return Decision(
            type=DecisionType.REVIEW,
            confidence=0.65,
            risk_score=0.35,
            savings_potential=int(f.annual_cost * 0.2),
            recommended_seats=None,
            factors={
                "renewal_days": f.renewal_days,
                "utilization_rate": f.utilization_rate
            },
            explanation=f"Renewal in {f.renewal_days} days - verify seat count"
        )

    # === DEFAULT: Keep ===
    return Decision(
        type=DecisionType.KEEP,
        confidence=0.7,
        risk_score=0.1,
        savings_potential=0,
        recommended_seats=None,
        factors={
            "utilization_rate": f.utilization_rate,
            "keystone_score": f.keystone_score
        },
        explanation="Tool is actively used and healthy"
    )
```

### Decision Thresholds

| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| Utilization | >70% | 50-70% | <50% |
| Last Activity | <30 days | 30-60 days | >60 days |
| Keystone Score | >0.7 | 0.3-0.7 | <0.3 |
| Renewal Urgency | >60 days | 30-60 days | <30 days |

---

## 5. Escalation Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    ESCALATION WORKFLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Day 0: Decision Generated                                       │
│     │                                                            │
│     ▼                                                            │
│  ┌─────────────────────────────────────────────┐                │
│  │ LEVEL 1: In-App + Email to Owner           │                │
│  │ "Review needed for [Tool] before renewal"  │                │
│  └─────────────────────┬───────────────────────┘                │
│                        │                                         │
│              No response in 3 days?                              │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────┐                │
│  │ LEVEL 2: Reminder Email + Slack DM         │                │
│  │ "Action required: [Tool] renews in X days" │                │
│  └─────────────────────┬───────────────────────┘                │
│                        │                                         │
│              No response in 3 days?                              │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────┐                │
│  │ LEVEL 3: Escalate to Manager + Finance     │                │
│  │ "Unresponsive owner - needs reassignment"  │                │
│  └─────────────────────┬───────────────────────┘                │
│                        │                                         │
│              No response in 3 days?                              │
│              AND renewal < 7 days?                               │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────┐                │
│  │ LEVEL 4: WhatsApp/SMS to Finance Lead      │                │
│  │ "URGENT: $X auto-renews in Y days"         │                │
│  │ (Only for high-cost subscriptions >$5k)    │                │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Escalation Rules

```python
ESCALATION_CONFIG = {
    "level_1": {
        "channels": ["in_app", "email"],
        "wait_days": 3,
        "template": "review_needed"
    },
    "level_2": {
        "channels": ["email", "slack"],
        "wait_days": 3,
        "template": "action_required"
    },
    "level_3": {
        "channels": ["email"],
        "recipients": ["manager", "finance_admin"],
        "wait_days": 3,
        "template": "escalation_manager"
    },
    "level_4": {
        "channels": ["whatsapp", "sms"],
        "recipients": ["finance_lead"],
        "conditions": {
            "min_cost_cents": 500000,  # $5000+
            "max_renewal_days": 7
        },
        "template": "urgent_renewal"
    }
}
```

---

## 6. MVP Roadmap (6 Weeks)

### Week 1-2: Foundation
- [ ] Database schema setup (Supabase)
- [ ] FastAPI backend scaffold
- [ ] Google Workspace SSO integration
- [ ] Basic user/org management
- [ ] Next.js frontend with auth

### Week 3: SaaS Discovery
- [ ] SSO-based app discovery (Google Admin API)
- [ ] Manual tool addition
- [ ] Basic tool catalog UI
- [ ] Tool access tracking

### Week 4: Billing & Subscriptions
- [ ] Subscription management CRUD
- [ ] Renewal calendar view
- [ ] Cost dashboard
- [ ] Owner assignment

### Week 5: Decision Engine
- [ ] Usage signal collection
- [ ] Decision engine (heuristics)
- [ ] Decision dashboard
- [ ] Basic dependency tracking

### Week 6: Communication & Polish
- [ ] Email notifications (SendGrid)
- [ ] Escalation workflow
- [ ] Audit logging
- [ ] Dashboard polish
- [ ] Documentation

### Post-MVP (Month 2-3)
- [ ] Microsoft Entra SSO
- [ ] Okta integration
- [ ] WhatsApp notifications
- [ ] Advanced graph analysis
- [ ] API integrations (Slack, Zoom, etc.)
- [ ] Billing imports (CSV, API)

---

## 7. API Structure

```
/api/v1/
├── /auth
│   ├── POST /login/google     # Google SSO
│   ├── POST /login/microsoft  # Microsoft SSO
│   └── POST /logout
│
├── /organizations
│   ├── GET /current           # Get current org
│   └── PATCH /settings        # Update settings
│
├── /users
│   ├── GET /                  # List users
│   ├── GET /:id               # Get user
│   └── PATCH /:id             # Update user
│
├── /tools
│   ├── GET /                  # List SaaS tools
│   ├── POST /                 # Add tool
│   ├── GET /:id               # Get tool details
│   ├── PATCH /:id             # Update tool
│   ├── GET /:id/users         # Users with access
│   └── GET /:id/dependencies  # Tool dependencies
│
├── /subscriptions
│   ├── GET /                  # List subscriptions
│   ├── POST /                 # Add subscription
│   ├── GET /:id               # Get subscription
│   ├── PATCH /:id             # Update subscription
│   └── GET /renewals          # Upcoming renewals
│
├── /decisions
│   ├── GET /                  # List decisions
│   ├── GET /:id               # Get decision
│   ├── POST /:id/approve      # Approve decision
│   ├── POST /:id/reject       # Reject decision
│   └── POST /generate         # Generate new decisions
│
├── /dashboard
│   ├── GET /summary           # Overview stats
│   ├── GET /savings           # Savings opportunities
│   └── GET /alerts            # Active alerts
│
└── /integrations
    ├── POST /google/connect   # Connect Google Workspace
    ├── POST /google/sync      # Sync Google data
    └── GET /status            # Integration status
```

---

## 8. Security & Compliance

### Data Handling
- No email content inspection
- No file/document access
- Only metadata: login times, seat assignments
- All data encrypted at rest (AES-256)
- TLS 1.3 in transit

### Access Control
- RBAC: Admin, Finance, IT, Member
- Org-level data isolation
- Audit logging for all actions

### Compliance Ready
- SOC 2 Type II (target)
- GDPR compliant
- Data retention policies

---

## 9. Pricing Model (Suggested)

| Plan | Users | Price | Features |
|------|-------|-------|----------|
| Starter | Up to 50 | $199/mo | Basic discovery, 5 integrations |
| Growth | Up to 200 | $499/mo | All integrations, decision engine |
| Enterprise | Unlimited | Custom | SSO, API, dedicated support |

---

## Next Steps

1. **Start with database schema** - Run the SQL above in Supabase
2. **Build auth flow** - Google Workspace SSO first
3. **Create tool discovery** - Pull apps from Google Admin
4. **Manual MVP** - Let users add subscriptions manually
5. **Add decision engine** - Heuristics first, no ML needed
