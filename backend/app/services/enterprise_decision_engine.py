"""
Enterprise Decision Engine for SaaS Governance

Conservative, explainable decision-making for subscription management.
Principles:
1. Default to KEEP unless strong signals
2. Never auto-cancel keystone tools
3. Always explain reasoning
4. Escalate when uncertain
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Optional


class DecisionType(str, Enum):
    KEEP = "keep"
    DOWNSIZE = "downsize"
    REVIEW = "review"
    CANCEL = "cancel"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class SubscriptionContext:
    """All context needed to make a decision about a subscription."""
    # Basic info
    subscription_id: str
    tool_id: str
    tool_name: str
    org_id: str

    # Seats & Usage
    paid_seats: int
    active_users: int
    last_activity_date: Optional[date]

    # Cost
    amount_cents: int
    billing_cycle: str  # monthly, yearly

    # Renewal
    renewal_date: Optional[date]
    auto_renew: bool
    contract_end_date: Optional[date]

    # Ownership
    owner_id: Optional[str]
    owner_active: bool
    owner_name: Optional[str]

    # Dependencies
    dependency_count: int
    keystone_score: float  # 0-1
    dependent_tools: list[str] = field(default_factory=list)

    # Category
    category: str = "other"


@dataclass
class DecisionFactor:
    """A single factor contributing to a decision."""
    name: str
    value: any
    weight: float
    impact: str  # positive, negative, neutral
    explanation: str


@dataclass
class Decision:
    """The final decision with full context."""
    type: DecisionType
    confidence: float  # 0-1
    risk_score: float  # 0-1, higher = more risky to act
    risk_level: RiskLevel
    priority: Priority

    # Savings
    savings_potential_cents: int
    recommended_seats: Optional[int]

    # Explanation
    explanation: str
    factors: list[DecisionFactor]

    # Metadata
    due_date: Optional[date]
    requires_approval: bool


class EnterpriseDecisionEngine:
    """
    Conservative decision engine for SaaS subscriptions.

    Thresholds:
    - Utilization: <30% = severe, 30-50% = moderate, 50-70% = acceptable, >70% = healthy
    - Inactivity: >60 days = critical, 30-60 = concerning, <30 = ok
    - Keystone: >0.7 = critical, 0.3-0.7 = important, <0.3 = normal
    """

    # Thresholds
    UTILIZATION_SEVERE = 0.30
    UTILIZATION_MODERATE = 0.50
    UTILIZATION_ACCEPTABLE = 0.70

    INACTIVITY_CRITICAL_DAYS = 60
    INACTIVITY_CONCERNING_DAYS = 30

    KEYSTONE_CRITICAL = 0.70
    KEYSTONE_IMPORTANT = 0.30

    RENEWAL_URGENT_DAYS = 7
    RENEWAL_SOON_DAYS = 30
    RENEWAL_UPCOMING_DAYS = 60

    # Minimum savings to recommend action
    MIN_SAVINGS_FOR_DOWNSIZE = 10000  # $100
    MIN_SAVINGS_FOR_CANCEL = 50000    # $500

    def make_decision(self, ctx: SubscriptionContext) -> Decision:
        """
        Make a decision about a subscription.

        Decision hierarchy:
        1. Keystone protection (KEEP)
        2. Owner departed (REVIEW)
        3. Zero usage (CANCEL)
        4. Severe underutilization (DOWNSIZE)
        5. Moderate underutilization (REVIEW)
        6. Upcoming renewal check (REVIEW)
        7. Default (KEEP)
        """
        factors = []

        # Calculate derived metrics
        utilization = ctx.active_users / ctx.paid_seats if ctx.paid_seats > 0 else 0
        days_inactive = self._days_since(ctx.last_activity_date) if ctx.last_activity_date else 999
        days_to_renewal = self._days_until(ctx.renewal_date) if ctx.renewal_date else 999
        annual_cost = self._annualized_cost(ctx.amount_cents, ctx.billing_cycle)

        # Add base factors
        factors.append(DecisionFactor(
            name="utilization_rate",
            value=utilization,
            weight=0.35,
            impact=self._rate_utilization(utilization),
            explanation=f"{ctx.active_users}/{ctx.paid_seats} seats used ({utilization:.0%})"
        ))

        factors.append(DecisionFactor(
            name="last_activity",
            value=days_inactive,
            weight=0.25,
            impact=self._rate_inactivity(days_inactive),
            explanation=f"Last activity {days_inactive} days ago" if days_inactive < 999 else "No activity data"
        ))

        factors.append(DecisionFactor(
            name="keystone_score",
            value=ctx.keystone_score,
            weight=0.20,
            impact="positive" if ctx.keystone_score > 0.3 else "neutral",
            explanation=f"{ctx.dependency_count} tools depend on this"
        ))

        factors.append(DecisionFactor(
            name="renewal_urgency",
            value=days_to_renewal,
            weight=0.10,
            impact=self._rate_renewal_urgency(days_to_renewal),
            explanation=f"Renewal in {days_to_renewal} days" if days_to_renewal < 999 else "No renewal date"
        ))

        factors.append(DecisionFactor(
            name="annual_cost",
            value=annual_cost,
            weight=0.10,
            impact="neutral",
            explanation=f"${annual_cost/100:,.0f}/year"
        ))

        # === RULE 1: Keystone Protection ===
        if ctx.keystone_score >= self.KEYSTONE_CRITICAL:
            return Decision(
                type=DecisionType.KEEP,
                confidence=0.95,
                risk_score=0.95,
                risk_level=RiskLevel.CRITICAL,
                priority=Priority.LOW,
                savings_potential_cents=0,
                recommended_seats=None,
                explanation=f"Critical infrastructure: {ctx.dependency_count} tools depend on {ctx.tool_name}",
                factors=factors,
                due_date=None,
                requires_approval=False
            )

        # === RULE 2: Owner Departed ===
        if not ctx.owner_active and ctx.owner_id:
            factors.append(DecisionFactor(
                name="owner_status",
                value="departed",
                weight=0.5,
                impact="negative",
                explanation=f"Owner {ctx.owner_name or 'unknown'} is no longer active"
            ))

            return Decision(
                type=DecisionType.REVIEW,
                confidence=0.85,
                risk_score=0.50,
                risk_level=RiskLevel.MEDIUM,
                priority=Priority.HIGH,
                savings_potential_cents=0,
                recommended_seats=None,
                explanation=f"Tool owner has left - needs ownership transfer",
                factors=factors,
                due_date=ctx.renewal_date,
                requires_approval=True
            )

        # === RULE 3: Zero Usage ===
        if ctx.active_users == 0 and days_inactive > self.INACTIVITY_CRITICAL_DAYS:
            risk = 0.20 + (ctx.keystone_score * 0.4)  # Higher risk if some dependencies

            return Decision(
                type=DecisionType.CANCEL,
                confidence=0.85,
                risk_score=risk,
                risk_level=RiskLevel.LOW if risk < 0.3 else RiskLevel.MEDIUM,
                priority=self._get_priority(days_to_renewal),
                savings_potential_cents=annual_cost,
                recommended_seats=None,
                explanation=f"No active users for {days_inactive} days",
                factors=factors,
                due_date=ctx.renewal_date or self._get_due_date(30),
                requires_approval=annual_cost > self.MIN_SAVINGS_FOR_CANCEL
            )

        # === RULE 4: Severe Underutilization ===
        if utilization < self.UTILIZATION_SEVERE and ctx.paid_seats > 5:
            optimal_seats = max(ctx.active_users + 2, 5)  # Keep buffer
            savings = int(((ctx.paid_seats - optimal_seats) / ctx.paid_seats) * annual_cost)

            if savings >= self.MIN_SAVINGS_FOR_DOWNSIZE:
                return Decision(
                    type=DecisionType.DOWNSIZE,
                    confidence=0.80,
                    risk_score=0.25,
                    risk_level=RiskLevel.LOW,
                    priority=self._get_priority(days_to_renewal),
                    savings_potential_cents=savings,
                    recommended_seats=optimal_seats,
                    explanation=f"Only {utilization:.0%} utilization - reduce from {ctx.paid_seats} to {optimal_seats} seats",
                    factors=factors,
                    due_date=ctx.renewal_date or self._get_due_date(30),
                    requires_approval=True
                )

        # === RULE 5: Moderate Underutilization ===
        if utilization < self.UTILIZATION_MODERATE:
            return Decision(
                type=DecisionType.REVIEW,
                confidence=0.65,
                risk_score=0.35,
                risk_level=RiskLevel.LOW,
                priority=Priority.NORMAL,
                savings_potential_cents=int(annual_cost * 0.3),
                recommended_seats=None,
                explanation=f"Underutilized at {utilization:.0%} - review seat allocation",
                factors=factors,
                due_date=ctx.renewal_date or self._get_due_date(60),
                requires_approval=False
            )

        # === RULE 6: Upcoming Renewal ===
        if days_to_renewal < self.RENEWAL_SOON_DAYS and utilization < self.UTILIZATION_ACCEPTABLE:
            return Decision(
                type=DecisionType.REVIEW,
                confidence=0.70,
                risk_score=0.30,
                risk_level=RiskLevel.LOW,
                priority=Priority.HIGH if days_to_renewal < self.RENEWAL_URGENT_DAYS else Priority.NORMAL,
                savings_potential_cents=int(annual_cost * 0.15),
                recommended_seats=None,
                explanation=f"Renewal in {days_to_renewal} days - verify seat count ({utilization:.0%} utilized)",
                factors=factors,
                due_date=ctx.renewal_date,
                requires_approval=False
            )

        # === DEFAULT: Keep ===
        return Decision(
            type=DecisionType.KEEP,
            confidence=0.75,
            risk_score=0.10,
            risk_level=RiskLevel.LOW,
            priority=Priority.LOW,
            savings_potential_cents=0,
            recommended_seats=None,
            explanation=f"Healthy usage ({utilization:.0%}) - no action needed",
            factors=factors,
            due_date=None,
            requires_approval=False
        )

    def _days_since(self, d: date) -> int:
        """Days since a date."""
        if not d:
            return 999
        return (date.today() - d).days

    def _days_until(self, d: date) -> int:
        """Days until a date."""
        if not d:
            return 999
        return (d - date.today()).days

    def _annualized_cost(self, amount_cents: int, billing_cycle: str) -> int:
        """Convert to annual cost."""
        if not amount_cents:
            return 0
        if billing_cycle == "monthly":
            return amount_cents * 12
        elif billing_cycle == "quarterly":
            return amount_cents * 4
        return amount_cents  # yearly

    def _rate_utilization(self, rate: float) -> str:
        """Rate utilization impact."""
        if rate >= self.UTILIZATION_ACCEPTABLE:
            return "positive"
        elif rate >= self.UTILIZATION_MODERATE:
            return "neutral"
        return "negative"

    def _rate_inactivity(self, days: int) -> str:
        """Rate inactivity impact."""
        if days <= self.INACTIVITY_CONCERNING_DAYS:
            return "positive"
        elif days <= self.INACTIVITY_CRITICAL_DAYS:
            return "neutral"
        return "negative"

    def _rate_renewal_urgency(self, days: int) -> str:
        """Rate renewal urgency."""
        if days <= self.RENEWAL_URGENT_DAYS:
            return "negative"
        elif days <= self.RENEWAL_SOON_DAYS:
            return "neutral"
        return "positive"

    def _get_priority(self, days_to_renewal: int) -> Priority:
        """Get priority based on renewal urgency."""
        if days_to_renewal <= self.RENEWAL_URGENT_DAYS:
            return Priority.URGENT
        elif days_to_renewal <= self.RENEWAL_SOON_DAYS:
            return Priority.HIGH
        elif days_to_renewal <= self.RENEWAL_UPCOMING_DAYS:
            return Priority.NORMAL
        return Priority.LOW

    def _get_due_date(self, days: int) -> date:
        """Get due date N days from now."""
        return date.today() + timedelta(days=days)


# Convenience function
def make_enterprise_decision(ctx: SubscriptionContext) -> Decision:
    """Make a decision using the enterprise engine."""
    engine = EnterpriseDecisionEngine()
    return engine.make_decision(ctx)
