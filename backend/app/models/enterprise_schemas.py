"""
Enterprise Pydantic Schemas for SaaS Governance Platform
"""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class OrgPlan(str, Enum):
    TRIAL = "trial"
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class UserRole(str, Enum):
    ADMIN = "admin"
    FINANCE = "finance"
    IT_ADMIN = "it_admin"
    MEMBER = "member"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OFFBOARDED = "offboarded"


class ToolCategory(str, Enum):
    PRODUCTIVITY = "productivity"
    DEV_TOOLS = "dev_tools"
    COMMUNICATION = "communication"
    SECURITY = "security"
    HR = "hr"
    FINANCE = "finance"
    MARKETING = "marketing"
    SALES = "sales"
    ANALYTICS = "analytics"
    OTHER = "other"


class ToolStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    UNDER_REVIEW = "under_review"
    SUNSET = "sunset"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class DecisionType(str, Enum):
    KEEP = "keep"
    DOWNSIZE = "downsize"
    REVIEW = "review"
    CANCEL = "cancel"


class DecisionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class IntegrationProvider(str, Enum):
    GOOGLE_WORKSPACE = "google_workspace"
    MICROSOFT_ENTRA = "microsoft_entra"
    OKTA = "okta"
    SLACK = "slack"


# =============================================================================
# ORGANIZATIONS
# =============================================================================

class OrganizationBase(BaseModel):
    name: str
    domain: str
    plan: OrgPlan = OrgPlan.TRIAL
    sso_provider: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[OrgPlan] = None
    sso_provider: Optional[str] = None
    sso_config: Optional[dict] = None
    settings: Optional[dict] = None


class Organization(OrganizationBase):
    id: str
    settings: dict = {}
    sso_config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# ORG USERS
# =============================================================================

class OrgUserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    role: UserRole = UserRole.MEMBER


class OrgUserCreate(OrgUserBase):
    manager_id: Optional[str] = None


class OrgUserUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    role: Optional[UserRole] = None
    manager_id: Optional[str] = None
    status: Optional[UserStatus] = None


class OrgUser(OrgUserBase):
    id: str
    org_id: str
    avatar_url: Optional[str] = None
    manager_id: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    sso_provider: Optional[str] = None
    sso_id: Optional[str] = None
    last_login_at: Optional[datetime] = None
    offboarded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrgUserWithManager(OrgUser):
    manager: Optional["OrgUser"] = None


# =============================================================================
# SAAS TOOLS
# =============================================================================

class SaaSToolBase(BaseModel):
    name: str
    category: Optional[ToolCategory] = ToolCategory.OTHER
    vendor_domain: Optional[str] = None
    vendor_url: Optional[str] = None
    description: Optional[str] = None


class SaaSToolCreate(SaaSToolBase):
    normalized_name: Optional[str] = None  # Auto-generated if not provided


class SaaSToolUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[ToolCategory] = None
    vendor_domain: Optional[str] = None
    vendor_url: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ToolStatus] = None
    is_keystone: Optional[bool] = None


class SaaSTool(SaaSToolBase):
    id: str
    org_id: str
    normalized_name: str
    logo_url: Optional[str] = None
    discovery_source: Optional[str] = None
    discovery_data: Optional[dict] = None
    status: ToolStatus = ToolStatus.ACTIVE
    is_keystone: bool = False
    keystone_score: float = 0
    metadata: dict = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SaaSToolWithStats(SaaSTool):
    active_users: int = 0
    total_users: int = 0
    monthly_cost: int = 0
    dependency_count: int = 0


# =============================================================================
# TOOL SUBSCRIPTIONS
# =============================================================================

class ToolSubscriptionBase(BaseModel):
    tool_id: str
    plan_name: Optional[str] = None
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    amount_cents: Optional[int] = None
    currency: str = "USD"
    paid_seats: Optional[int] = None
    renewal_date: Optional[date] = None
    auto_renew: bool = True


class ToolSubscriptionCreate(ToolSubscriptionBase):
    owner_id: Optional[str] = None
    department: Optional[str] = None
    cost_center: Optional[str] = None


class ToolSubscriptionUpdate(BaseModel):
    plan_name: Optional[str] = None
    billing_cycle: Optional[BillingCycle] = None
    amount_cents: Optional[int] = None
    paid_seats: Optional[int] = None
    active_seats: Optional[int] = None
    renewal_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    auto_renew: Optional[bool] = None
    owner_id: Optional[str] = None
    department: Optional[str] = None
    cost_center: Optional[str] = None
    status: Optional[SubscriptionStatus] = None
    notes: Optional[str] = None


class ToolSubscription(ToolSubscriptionBase):
    id: str
    org_id: str
    active_seats: int = 0
    contract_start_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    cancellation_notice_days: int = 30
    owner_id: Optional[str] = None
    department: Optional[str] = None
    cost_center: Optional[str] = None
    purchase_order: Optional[str] = None
    notes: Optional[str] = None
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    billing_source: Optional[str] = None
    billing_data: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ToolSubscriptionWithDetails(ToolSubscription):
    tool_name: str
    owner_name: Optional[str] = None
    owner_status: Optional[str] = None
    utilization_rate: float = 0
    days_until_renewal: Optional[int] = None


# =============================================================================
# TOOL ACCESS
# =============================================================================

class ToolAccessBase(BaseModel):
    tool_id: str
    user_id: str
    access_level: str = "user"
    license_type: Optional[str] = None


class ToolAccessCreate(ToolAccessBase):
    granted_by: Optional[str] = None


class ToolAccessUpdate(BaseModel):
    access_level: Optional[str] = None
    license_type: Optional[str] = None
    status: Optional[str] = None


class ToolAccess(ToolAccessBase):
    id: str
    org_id: str
    granted_at: datetime
    granted_by: Optional[str] = None
    last_active_at: Optional[datetime] = None
    activity_days_30: int = 0
    activity_days_90: int = 0
    activity_score: float = 0
    status: str = "active"
    metadata: dict = {}

    class Config:
        from_attributes = True


class ToolAccessWithUser(ToolAccess):
    user_name: Optional[str] = None
    user_email: str
    user_department: Optional[str] = None


# =============================================================================
# DECISIONS
# =============================================================================

class DecisionFactor(BaseModel):
    name: str
    value: float | str | int
    weight: float
    impact: str
    explanation: str


class DecisionBase(BaseModel):
    subscription_id: Optional[str] = None
    tool_id: Optional[str] = None
    decision_type: DecisionType
    reason: Optional[str] = None


class DecisionCreate(DecisionBase):
    confidence: float = 0.5
    risk_score: float = 0.5
    savings_potential_cents: int = 0
    recommended_seats: Optional[int] = None
    factors: Optional[list[DecisionFactor]] = None
    explanation: Optional[str] = None
    priority: Priority = Priority.NORMAL
    due_date: Optional[date] = None


class DecisionUpdate(BaseModel):
    status: Optional[DecisionStatus] = None
    decided_by: Optional[str] = None
    execution_notes: Optional[str] = None


class Decision(DecisionBase):
    id: str
    org_id: str
    confidence: float
    risk_score: float
    risk_factors: Optional[dict] = None
    savings_potential_cents: int = 0
    current_seats: Optional[int] = None
    recommended_seats: Optional[int] = None
    factors: Optional[list] = None
    explanation: Optional[str] = None
    status: DecisionStatus = DecisionStatus.PENDING
    priority: Priority = Priority.NORMAL
    due_date: Optional[date] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    execution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DecisionWithDetails(Decision):
    tool_name: Optional[str] = None
    subscription_plan: Optional[str] = None
    decided_by_name: Optional[str] = None


# =============================================================================
# TOOL DEPENDENCIES
# =============================================================================

class ToolDependencyBase(BaseModel):
    source_tool_id: str
    target_tool_id: str
    dependency_type: str
    strength: float = 0.5
    description: Optional[str] = None


class ToolDependencyCreate(ToolDependencyBase):
    pass


class ToolDependency(ToolDependencyBase):
    id: str
    org_id: str
    direction: str = "outgoing"
    auto_discovered: bool = False
    verified: bool = False
    discovered_at: datetime

    class Config:
        from_attributes = True


class ToolDependencyWithNames(ToolDependency):
    source_tool_name: str
    target_tool_name: str


# =============================================================================
# INTEGRATIONS
# =============================================================================

class IntegrationBase(BaseModel):
    provider: IntegrationProvider


class IntegrationCreate(IntegrationBase):
    access_token: str
    refresh_token: Optional[str] = None
    scopes: list[str] = []


class IntegrationUpdate(BaseModel):
    status: Optional[str] = None
    config: Optional[dict] = None


class Integration(IntegrationBase):
    id: str
    org_id: str
    status: str = "pending"
    token_expires_at: Optional[datetime] = None
    scopes: list[str] = []
    last_sync_at: Optional[datetime] = None
    sync_status: Optional[str] = None
    sync_error: Optional[str] = None
    config: dict = {}
    metadata: dict = {}
    connected_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# DASHBOARD / ANALYTICS
# =============================================================================

class DashboardStats(BaseModel):
    total_tools: int = 0
    active_subscriptions: int = 0
    total_users: int = 0
    monthly_spend_cents: int = 0
    annual_spend_cents: int = 0
    potential_savings_cents: int = 0
    pending_decisions: int = 0
    tools_under_review: int = 0
    avg_utilization: float = 0


class SpendByCategory(BaseModel):
    category: str
    amount_cents: int
    tool_count: int


class UpcomingRenewal(BaseModel):
    subscription_id: str
    tool_name: str
    renewal_date: date
    amount_cents: int
    days_until: int
    urgency: str


# =============================================================================
# API RESPONSES
# =============================================================================

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


class BulkActionResponse(BaseModel):
    success_count: int
    error_count: int
    errors: list[dict] = []
