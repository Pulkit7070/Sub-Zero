"""Decision engine for subscription recommendations."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import UUID


class DecisionType(str, Enum):
    CANCEL = "cancel"
    KEEP = "keep"
    REVIEW = "review"
    REMIND = "remind"


@dataclass
class Decision:
    """A recommendation decision for a subscription."""
    subscription_id: UUID
    decision_type: DecisionType
    reason: str
    confidence: float


class DecisionEngine:
    """
    Rule-based decision engine for subscription recommendations.

    Rules:
    1. No emails in 90+ days → CANCEL (high confidence)
    2. Expensive (>$20/mo) + low activity → REVIEW
    3. Renewal in 7 days → REMIND
    4. Active usage → KEEP
    """

    # Thresholds
    INACTIVE_DAYS = 90
    EXPENSIVE_THRESHOLD_CENTS = 2000  # $20
    RENEWAL_REMINDER_DAYS = 7
    LOW_ACTIVITY_THRESHOLD = 2  # emails in last 90 days

    def __init__(self, email_counts: Optional[dict[UUID, int]] = None):
        """
        Initialize decision engine.

        Args:
            email_counts: Map of subscription_id -> email count in last 90 days
        """
        self.email_counts = email_counts or {}

    def evaluate(self, subscription: dict) -> Decision:
        """
        Evaluate a subscription and generate a recommendation.

        Args:
            subscription: Dictionary with subscription data

        Returns:
            Decision object with recommendation
        """
        subscription_id = subscription["id"]
        last_charge_at = subscription.get("last_charge_at")
        next_renewal_at = subscription.get("next_renewal_at")
        amount_cents = subscription.get("amount_cents")
        status = subscription.get("status", "active")

        # Skip if already cancelled
        if status == "cancelled":
            return Decision(
                subscription_id=subscription_id,
                decision_type=DecisionType.KEEP,
                reason="Already cancelled",
                confidence=1.0,
            )

        now = datetime.now(timezone.utc)

        # Rule 1: Check for inactivity (no charge in 90+ days)
        if last_charge_at:
            days_since_charge = (now - last_charge_at).days
            if days_since_charge > self.INACTIVE_DAYS:
                return Decision(
                    subscription_id=subscription_id,
                    decision_type=DecisionType.CANCEL,
                    reason=f"No activity in {days_since_charge} days. Consider cancelling to save money.",
                    confidence=0.85,
                )

        # Get email activity for this subscription
        email_count = self.email_counts.get(subscription_id, 0)

        # Rule 2: Expensive + low activity
        if amount_cents and amount_cents >= self.EXPENSIVE_THRESHOLD_CENTS:
            if email_count <= self.LOW_ACTIVITY_THRESHOLD:
                monthly_cost = amount_cents / 100
                return Decision(
                    subscription_id=subscription_id,
                    decision_type=DecisionType.REVIEW,
                    reason=f"Costing ${monthly_cost:.2f}/mo with minimal usage. Review if you still need it.",
                    confidence=0.75,
                )

        # Rule 3: Upcoming renewal
        if next_renewal_at:
            days_until_renewal = (next_renewal_at - now).days
            if 0 <= days_until_renewal <= self.RENEWAL_REMINDER_DAYS:
                amount_str = f"${amount_cents/100:.2f}" if amount_cents else "unknown amount"
                return Decision(
                    subscription_id=subscription_id,
                    decision_type=DecisionType.REMIND,
                    reason=f"Renews in {days_until_renewal} days for {amount_str}. Decide if you want to continue.",
                    confidence=0.9,
                )

        # Rule 4: Default - appears active
        return Decision(
            subscription_id=subscription_id,
            decision_type=DecisionType.KEEP,
            reason="Subscription appears to be in active use.",
            confidence=0.7,
        )

    def evaluate_all(self, subscriptions: list[dict]) -> list[Decision]:
        """
        Evaluate all subscriptions and generate recommendations.

        Args:
            subscriptions: List of subscription dictionaries

        Returns:
            List of Decision objects
        """
        return [self.evaluate(sub) for sub in subscriptions]

    def get_actionable_decisions(
        self,
        subscriptions: list[dict],
    ) -> list[Decision]:
        """
        Get only actionable decisions (not KEEP).

        Args:
            subscriptions: List of subscription dictionaries

        Returns:
            List of actionable Decision objects
        """
        all_decisions = self.evaluate_all(subscriptions)
        return [d for d in all_decisions if d.decision_type != DecisionType.KEEP]


def calculate_potential_savings(decisions: list[Decision], subscriptions: dict[UUID, dict]) -> int:
    """
    Calculate potential monthly savings from cancel/review decisions.

    Args:
        decisions: List of decisions
        subscriptions: Map of subscription_id -> subscription data

    Returns:
        Total potential savings in cents
    """
    total_cents = 0

    for decision in decisions:
        if decision.decision_type in [DecisionType.CANCEL, DecisionType.REVIEW]:
            sub = subscriptions.get(decision.subscription_id)
            if sub and sub.get("amount_cents"):
                total_cents += sub["amount_cents"]

    return total_cents
