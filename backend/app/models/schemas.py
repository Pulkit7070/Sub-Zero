"""Pydantic models for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# Enums
class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    EXPIRED = "expired"


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    WEEKLY = "weekly"
    QUARTERLY = "quarterly"
    ONE_TIME = "one_time"


class DecisionType(str, Enum):
    CANCEL = "cancel"
    KEEP = "keep"
    REVIEW = "review"
    REMIND = "remind"


class UserAction(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SNOOZED = "snoozed"


class DataSourceProvider(str, Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    MANUAL = "manual"


# User models
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime


# DataSource models
class DataSourceBase(BaseModel):
    provider: DataSourceProvider


class DataSourceCreate(DataSourceBase):
    user_id: UUID
    access_token_encrypted: str
    refresh_token_encrypted: Optional[str] = None
    token_expires_at: Optional[datetime] = None


class DataSource(DataSourceBase):
    id: UUID
    user_id: UUID
    status: str = "active"
    last_sync_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DataSourceResponse(BaseModel):
    id: UUID
    provider: str
    status: str
    last_sync_at: Optional[datetime]
    created_at: datetime


# Subscription models
class SubscriptionBase(BaseModel):
    vendor_name: str
    amount_cents: Optional[int] = None
    currency: str = "USD"
    billing_cycle: Optional[BillingCycle] = None


class SubscriptionCreate(SubscriptionBase):
    user_id: UUID
    vendor_normalized: Optional[str] = None
    last_charge_at: Optional[datetime] = None
    next_renewal_at: Optional[datetime] = None
    source: str = "gmail"
    confidence: float = 1.0
    raw_data: Optional[dict[str, Any]] = None


class SubscriptionUpdate(BaseModel):
    vendor_name: Optional[str] = None
    amount_cents: Optional[int] = None
    currency: Optional[str] = None
    billing_cycle: Optional[BillingCycle] = None
    status: Optional[SubscriptionStatus] = None
    next_renewal_at: Optional[datetime] = None


class Subscription(SubscriptionBase):
    id: UUID
    user_id: UUID
    vendor_normalized: Optional[str]
    last_charge_at: Optional[datetime]
    next_renewal_at: Optional[datetime]
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    source: str
    confidence: float
    raw_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: UUID
    vendor_name: str
    vendor_normalized: Optional[str]
    amount_cents: Optional[int]
    currency: str
    billing_cycle: Optional[str]
    last_charge_at: Optional[datetime]
    next_renewal_at: Optional[datetime]
    status: str
    source: str
    confidence: float
    created_at: datetime
    updated_at: datetime

    @property
    def amount_display(self) -> str:
        """Return formatted amount string."""
        if self.amount_cents is None:
            return "Unknown"
        return f"${self.amount_cents / 100:.2f}"


# UsageSignal models
class UsageSignalBase(BaseModel):
    signal_type: str
    signal_value: Optional[dict[str, Any]] = None


class UsageSignalCreate(UsageSignalBase):
    subscription_id: UUID


class UsageSignal(UsageSignalBase):
    id: UUID
    subscription_id: UUID
    recorded_at: datetime

    class Config:
        from_attributes = True


# Decision models
class DecisionBase(BaseModel):
    decision_type: DecisionType
    reason: Optional[str] = None
    confidence: Optional[float] = None


class DecisionCreate(DecisionBase):
    user_id: UUID
    subscription_id: UUID


class DecisionAction(BaseModel):
    action: UserAction


class Decision(DecisionBase):
    id: UUID
    user_id: UUID
    subscription_id: UUID
    user_action: Optional[UserAction]
    acted_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class DecisionResponse(BaseModel):
    id: UUID
    subscription_id: UUID
    subscription: Optional[SubscriptionResponse] = None
    decision_type: str
    reason: Optional[str]
    confidence: Optional[float]
    user_action: Optional[str]
    acted_at: Optional[datetime]
    created_at: datetime


# Auth models
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    email: Optional[str] = None


class GoogleAuthCallback(BaseModel):
    code: str
    state: Optional[str] = None


# Sync models
class SyncRequest(BaseModel):
    force: bool = False
    days_back: int = Field(default=90, ge=30, le=365)  # Max 90 days for first sync


class SyncResponse(BaseModel):
    status: str  # "completed", "partial", "failed", "locked"
    subscriptions_found: int
    new_subscriptions: int
    updated_subscriptions: int
    emails_processed: int
    emails_skipped: int  # already processed
    is_incremental: bool
    sync_from_date: Optional[datetime] = None
    message: Optional[str] = None
