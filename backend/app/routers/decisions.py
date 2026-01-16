"""Decision management endpoints."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.schemas import DecisionResponse, DecisionAction, SubscriptionResponse
from app.routers.auth import verify_token
from app.services.decision_engine import DecisionEngine, calculate_potential_savings

router = APIRouter()
settings = get_settings()


async def get_current_user_id(
    access_token: Optional[str] = Cookie(default=None),
) -> UUID:
    """Get current user ID from token."""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = verify_token(access_token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return UUID(payload["sub"])


@router.get("", response_model=list[DecisionResponse])
async def list_decisions(
    pending_only: bool = True,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List decisions for the current user."""
    query = """
        SELECT d.id, d.subscription_id, d.decision_type, d.reason,
               d.confidence, d.user_action, d.acted_at, d.created_at,
               s.vendor_name, s.vendor_normalized, s.amount_cents, s.currency,
               s.billing_cycle, s.last_charge_at, s.next_renewal_at, s.status,
               s.source, s.confidence as sub_confidence, s.created_at as sub_created,
               s.updated_at as sub_updated
        FROM decisions d
        JOIN subscriptions s ON d.subscription_id = s.id
        WHERE d.user_id = :user_id
    """

    if pending_only:
        query += " AND d.user_action IS NULL"

    query += " ORDER BY d.created_at DESC"

    result = await db.execute(query, {"user_id": str(user_id)})
    rows = result.fetchall()

    return [
        DecisionResponse(
            id=row[0],
            subscription_id=row[1],
            decision_type=row[2],
            reason=row[3],
            confidence=row[4],
            user_action=row[5],
            acted_at=row[6],
            created_at=row[7],
            subscription=SubscriptionResponse(
                id=row[1],
                vendor_name=row[8],
                vendor_normalized=row[9],
                amount_cents=row[10],
                currency=row[11],
                billing_cycle=row[12],
                last_charge_at=row[13],
                next_renewal_at=row[14],
                status=row[15],
                source=row[16],
                confidence=row[17],
                created_at=row[18],
                updated_at=row[19],
            ),
        )
        for row in rows
    ]


@router.post("/generate")
async def generate_decisions(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate new decisions based on current subscriptions."""
    # Get all active subscriptions
    sub_result = await db.execute(
        """
        SELECT id, vendor_name, vendor_normalized, amount_cents, currency,
               billing_cycle, last_charge_at, next_renewal_at, status,
               source, confidence, created_at, updated_at
        FROM subscriptions
        WHERE user_id = :user_id AND status = 'active'
        """,
        {"user_id": str(user_id)},
    )
    sub_rows = sub_result.fetchall()

    if not sub_rows:
        return {
            "status": "completed",
            "decisions_generated": 0,
            "potential_savings_cents": 0,
            "message": "No active subscriptions found.",
        }

    # Convert to dictionaries
    subscriptions = [
        {
            "id": row[0],
            "vendor_name": row[1],
            "vendor_normalized": row[2],
            "amount_cents": row[3],
            "currency": row[4],
            "billing_cycle": row[5],
            "last_charge_at": row[6],
            "next_renewal_at": row[7],
            "status": row[8],
            "source": row[9],
            "confidence": row[10],
            "created_at": row[11],
            "updated_at": row[12],
        }
        for row in sub_rows
    ]

    # Get existing pending decisions to avoid duplicates
    existing_result = await db.execute(
        """
        SELECT subscription_id
        FROM decisions
        WHERE user_id = :user_id AND user_action IS NULL
        """,
        {"user_id": str(user_id)},
    )
    existing_sub_ids = {row[0] for row in existing_result.fetchall()}

    # Run decision engine
    engine = DecisionEngine()
    decisions = engine.get_actionable_decisions(subscriptions)

    # Filter out subscriptions that already have pending decisions
    new_decisions = [d for d in decisions if d.subscription_id not in existing_sub_ids]

    # Insert new decisions
    for decision in new_decisions:
        await db.execute(
            """
            INSERT INTO decisions (
                user_id, subscription_id, decision_type, reason, confidence
            ) VALUES (
                :user_id, :subscription_id, :decision_type, :reason, :confidence
            )
            """,
            {
                "user_id": str(user_id),
                "subscription_id": str(decision.subscription_id),
                "decision_type": decision.decision_type.value,
                "reason": decision.reason,
                "confidence": decision.confidence,
            },
        )

    await db.commit()

    # Calculate potential savings
    sub_map = {s["id"]: s for s in subscriptions}
    potential_savings = calculate_potential_savings(new_decisions, sub_map)

    return {
        "status": "completed",
        "decisions_generated": len(new_decisions),
        "potential_savings_cents": potential_savings,
        "message": f"Generated {len(new_decisions)} new recommendations.",
    }


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific decision."""
    result = await db.execute(
        """
        SELECT d.id, d.subscription_id, d.decision_type, d.reason,
               d.confidence, d.user_action, d.acted_at, d.created_at,
               s.vendor_name, s.vendor_normalized, s.amount_cents, s.currency,
               s.billing_cycle, s.last_charge_at, s.next_renewal_at, s.status,
               s.source, s.confidence as sub_confidence, s.created_at as sub_created,
               s.updated_at as sub_updated
        FROM decisions d
        JOIN subscriptions s ON d.subscription_id = s.id
        WHERE d.id = :decision_id AND d.user_id = :user_id
        """,
        {"decision_id": str(decision_id), "user_id": str(user_id)},
    )

    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found",
        )

    return DecisionResponse(
        id=row[0],
        subscription_id=row[1],
        decision_type=row[2],
        reason=row[3],
        confidence=row[4],
        user_action=row[5],
        acted_at=row[6],
        created_at=row[7],
        subscription=SubscriptionResponse(
            id=row[1],
            vendor_name=row[8],
            vendor_normalized=row[9],
            amount_cents=row[10],
            currency=row[11],
            billing_cycle=row[12],
            last_charge_at=row[13],
            next_renewal_at=row[14],
            status=row[15],
            source=row[16],
            confidence=row[17],
            created_at=row[18],
            updated_at=row[19],
        ),
    )


@router.post("/{decision_id}/act")
async def act_on_decision(
    decision_id: UUID,
    action: DecisionAction,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Act on a decision (accept, reject, or snooze)."""
    # Verify decision exists and belongs to user
    check_result = await db.execute(
        """
        SELECT id, subscription_id, decision_type, user_action
        FROM decisions
        WHERE id = :decision_id AND user_id = :user_id
        """,
        {"decision_id": str(decision_id), "user_id": str(user_id)},
    )

    row = check_result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found",
        )

    if row[3] is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision has already been acted upon",
        )

    subscription_id = row[1]
    decision_type = row[2]

    # Update decision
    await db.execute(
        """
        UPDATE decisions
        SET user_action = :action, acted_at = NOW()
        WHERE id = :decision_id
        """,
        {"decision_id": str(decision_id), "action": action.action.value},
    )

    # If user accepted a cancel recommendation, mark subscription as cancelled
    if action.action.value == "accepted" and decision_type == "cancel":
        await db.execute(
            """
            UPDATE subscriptions
            SET status = 'cancelled', updated_at = NOW()
            WHERE id = :subscription_id
            """,
            {"subscription_id": str(subscription_id)},
        )

    await db.commit()

    action_message = {
        "accepted": "Recommendation accepted. ",
        "rejected": "Recommendation rejected. ",
        "snoozed": "Recommendation snoozed. ",
    }

    extra_message = ""
    if action.action.value == "accepted" and decision_type == "cancel":
        extra_message = "Subscription marked as cancelled."

    return {
        "status": "success",
        "message": action_message.get(action.action.value, "") + extra_message,
    }


@router.get("/summary/stats")
async def get_decision_stats(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get decision statistics for the current user."""
    # Count pending decisions
    pending_result = await db.execute(
        """
        SELECT COUNT(*)
        FROM decisions
        WHERE user_id = :user_id AND user_action IS NULL
        """,
        {"user_id": str(user_id)},
    )
    pending_count = pending_result.fetchone()[0]

    # Count accepted decisions
    accepted_result = await db.execute(
        """
        SELECT COUNT(*)
        FROM decisions
        WHERE user_id = :user_id AND user_action = 'accepted'
        """,
        {"user_id": str(user_id)},
    )
    accepted_count = accepted_result.fetchone()[0]

    # Calculate potential savings from pending cancel/review decisions
    savings_result = await db.execute(
        """
        SELECT COALESCE(SUM(s.amount_cents), 0)
        FROM decisions d
        JOIN subscriptions s ON d.subscription_id = s.id
        WHERE d.user_id = :user_id
          AND d.user_action IS NULL
          AND d.decision_type IN ('cancel', 'review')
        """,
        {"user_id": str(user_id)},
    )
    potential_savings = savings_result.fetchone()[0]

    # Calculate actual savings from accepted cancel decisions
    actual_result = await db.execute(
        """
        SELECT COALESCE(SUM(s.amount_cents), 0)
        FROM decisions d
        JOIN subscriptions s ON d.subscription_id = s.id
        WHERE d.user_id = :user_id
          AND d.user_action = 'accepted'
          AND d.decision_type = 'cancel'
        """,
        {"user_id": str(user_id)},
    )
    actual_savings = actual_result.fetchone()[0]

    return {
        "pending_decisions": pending_count,
        "accepted_decisions": accepted_count,
        "potential_savings_cents": potential_savings,
        "actual_savings_cents": actual_savings,
    }
