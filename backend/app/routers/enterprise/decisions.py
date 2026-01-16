"""
Enterprise Decisions API Router
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from datetime import date, datetime
import json

from ...database import get_db
from ...models.enterprise_schemas import (
    Decision,
    DecisionCreate,
    DecisionUpdate,
    DecisionWithDetails,
    DecisionStatus,
    DecisionType,
    Priority,
    PaginatedResponse,
)

router = APIRouter(prefix="/organizations/{org_id}/decisions", tags=["Decisions"])


@router.post("/analyze/{sub_id}")
async def analyze_subscription(
    org_id: str,
    sub_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Analyze a subscription and generate a decision recommendation."""
    # Get subscription with related data
    sub_result = await db.execute(
        text("SELECT * FROM tool_subscriptions WHERE org_id = :org_id AND id = :sub_id"),
        {"org_id": org_id, "sub_id": sub_id}
    )
    sub = sub_result.fetchone()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Get tool
    tool_result = await db.execute(
        text("SELECT * FROM saas_tools WHERE id = :tool_id"),
        {"tool_id": sub.tool_id}
    )
    tool = tool_result.fetchone()

    # Get owner
    owner = None
    if sub.owner_id:
        owner_result = await db.execute(
            text("SELECT * FROM org_users WHERE id = :owner_id"),
            {"owner_id": sub.owner_id}
        )
        owner = owner_result.fetchone()

    # Get dependencies (tools that depend on this one)
    deps_result = await db.execute(
        text("SELECT source_tool_id FROM tool_dependencies WHERE target_tool_id = :tool_id"),
        {"tool_id": sub.tool_id}
    )
    deps = deps_result.fetchall()

    # Calculate decision factors
    paid_seats = sub.paid_seats or 0
    active_seats = sub.active_seats or 0
    utilization = active_seats / paid_seats if paid_seats > 0 else 0

    # Determine decision type and factors
    factors = []
    decision_type = "keep"
    risk_score = 0
    savings_potential = 0
    confidence = 0.7

    # Utilization factor
    if utilization < 0.3:
        factors.append({
            "name": "low_utilization",
            "value": f"{utilization*100:.0f}%",
            "weight": 0.4,
            "impact": -0.8,
            "explanation": f"Only {active_seats} of {paid_seats} seats are being used"
        })
        decision_type = "cancel" if utilization == 0 else "downsize"
        risk_score = 0.2
        savings_potential = int(sub.amount_cents * (1 - utilization) * 0.8)
        confidence = 0.85
    elif utilization < 0.5:
        factors.append({
            "name": "moderate_utilization",
            "value": f"{utilization*100:.0f}%",
            "weight": 0.3,
            "impact": -0.4,
            "explanation": f"Utilization below 50%: {active_seats}/{paid_seats} seats"
        })
        decision_type = "downsize"
        savings_potential = int(sub.amount_cents * (1 - utilization) * 0.5)
        confidence = 0.75
    else:
        factors.append({
            "name": "healthy_utilization",
            "value": f"{utilization*100:.0f}%",
            "weight": 0.3,
            "impact": 0.3,
            "explanation": f"Good utilization: {active_seats}/{paid_seats} seats"
        })

    # Owner status factor
    if owner and owner.status == "offboarded":
        factors.append({
            "name": "departed_owner",
            "value": owner.name,
            "weight": 0.3,
            "impact": -0.6,
            "explanation": f"Owner {owner.name} has left the organization"
        })
        risk_score += 0.3

    # Dependencies factor
    if len(deps) > 3:
        factors.append({
            "name": "keystone_tool",
            "value": str(len(deps)),
            "weight": 0.3,
            "impact": 0.5,
            "explanation": f"{len(deps)} other tools depend on this"
        })
        if decision_type == "cancel":
            decision_type = "downsize"  # Don't cancel keystone tools
            confidence = 0.6

    # Priority based on renewal date
    priority = "normal"
    due_date = None
    if sub.renewal_date:
        days_until = (sub.renewal_date - date.today()).days
        due_date = sub.renewal_date
        if days_until <= 7:
            priority = "urgent"
        elif days_until <= 30:
            priority = "high"

    return {
        "subscription_id": sub_id,
        "tool_name": tool.name if tool else "Unknown",
        "decision": {
            "type": decision_type,
            "confidence": confidence,
            "risk_score": risk_score,
            "risk_level": "low" if risk_score < 0.3 else "medium" if risk_score < 0.6 else "high",
            "priority": priority,
            "savings_potential_cents": savings_potential,
            "recommended_seats": active_seats + max(1, active_seats // 10),
            "explanation": f"Based on {utilization*100:.0f}% utilization and {len(deps)} dependencies",
            "factors": factors,
            "due_date": due_date.isoformat() if due_date else None,
            "requires_approval": decision_type in ["cancel", "downsize"]
        }
    }


@router.post("/analyze-all")
async def analyze_all_subscriptions(
    org_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Analyze all active subscriptions and create decision records."""
    # Get all active subscriptions
    subs_result = await db.execute(
        text("SELECT id FROM tool_subscriptions WHERE org_id = :org_id AND status = 'active'"),
        {"org_id": org_id}
    )
    subs = subs_result.fetchall()

    if not subs:
        return {"message": "No active subscriptions to analyze", "count": 0}

    decisions_created = 0
    results = []

    for sub_record in subs:
        sub_id = str(sub_record.id)

        try:
            # Get full subscription data
            sub_result = await db.execute(
                text("SELECT * FROM tool_subscriptions WHERE id = :sub_id"),
                {"sub_id": sub_id}
            )
            sub = sub_result.fetchone()

            # Get tool
            tool_result = await db.execute(
                text("SELECT * FROM saas_tools WHERE id = :tool_id"),
                {"tool_id": sub.tool_id}
            )
            tool = tool_result.fetchone()

            # Get owner
            owner = None
            if sub.owner_id:
                owner_result = await db.execute(
                    text("SELECT * FROM org_users WHERE id = :owner_id"),
                    {"owner_id": sub.owner_id}
                )
                owner = owner_result.fetchone()

            # Get dependencies
            deps_result = await db.execute(
                text("SELECT source_tool_id FROM tool_dependencies WHERE target_tool_id = :tool_id"),
                {"tool_id": sub.tool_id}
            )
            deps = deps_result.fetchall()

            # Calculate utilization
            paid_seats = sub.paid_seats or 0
            active_seats = sub.active_seats or 0
            utilization = active_seats / paid_seats if paid_seats > 0 else 0

            # Determine decision type
            decision_type = "keep"
            savings_potential = 0
            confidence = 0.7

            if utilization == 0:
                decision_type = "cancel"
                savings_potential = sub.amount_cents or 0
                confidence = 0.9
            elif utilization < 0.3:
                decision_type = "downsize"
                savings_potential = int((sub.amount_cents or 0) * (1 - utilization) * 0.8)
                confidence = 0.85
            elif utilization < 0.5:
                decision_type = "downsize"
                savings_potential = int((sub.amount_cents or 0) * (1 - utilization) * 0.5)
                confidence = 0.75

            # Priority based on renewal date
            priority = "normal"
            due_date = None
            if sub.renewal_date:
                days_until = (sub.renewal_date - date.today()).days
                due_date = sub.renewal_date
                if days_until <= 7:
                    priority = "urgent"
                elif days_until <= 30:
                    priority = "high"

            # Only create decision record for non-KEEP decisions
            if decision_type != "keep":
                factors = [{"name": "utilization", "value": f"{utilization*100:.0f}%", "weight": 0.5, "impact": -0.5 if utilization < 0.5 else 0.3, "explanation": f"{active_seats}/{paid_seats} seats used"}]

                await db.execute(
                    text("""
                        INSERT INTO decisions (org_id, subscription_id, tool_id, decision_type, confidence, risk_score, savings_potential_cents, current_seats, recommended_seats, factors, explanation, status, priority, due_date)
                        VALUES (:org_id, :subscription_id, :tool_id, :decision_type, :confidence, :risk_score, :savings_potential_cents, :current_seats, :recommended_seats, :factors, :explanation, 'pending', :priority, :due_date)
                    """),
                    {
                        "org_id": org_id,
                        "subscription_id": sub_id,
                        "tool_id": str(sub.tool_id),
                        "decision_type": decision_type,
                        "confidence": confidence,
                        "risk_score": 0.3 if decision_type == "cancel" else 0.2,
                        "savings_potential_cents": savings_potential,
                        "current_seats": paid_seats,
                        "recommended_seats": active_seats + max(1, active_seats // 10),
                        "factors": json.dumps(factors),
                        "explanation": f"Based on {utilization*100:.0f}% utilization",
                        "priority": priority,
                        "due_date": due_date.isoformat() if due_date else None,
                    }
                )
                decisions_created += 1

            results.append({
                "subscription_id": sub_id,
                "tool_name": tool.name if tool else "Unknown",
                "decision_type": decision_type,
                "savings_potential": savings_potential
            })

        except Exception as e:
            results.append({
                "subscription_id": sub_id,
                "error": str(e)
            })

    await db.commit()

    return {
        "message": f"Analysis complete. Created {decisions_created} decision records.",
        "decisions_created": decisions_created,
        "subscriptions_analyzed": len(subs),
        "results": results
    }


@router.post("", response_model=Decision)
async def create_decision(
    org_id: str,
    decision: DecisionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Manually create a decision."""
    factors_json = json.dumps([f.model_dump() for f in decision.factors]) if decision.factors else None

    result = await db.execute(
        text("""
            INSERT INTO decisions (org_id, subscription_id, tool_id, decision_type, reason, confidence, risk_score, savings_potential_cents, recommended_seats, factors, explanation, status, priority, due_date)
            VALUES (:org_id, :subscription_id, :tool_id, :decision_type, :reason, :confidence, :risk_score, :savings_potential_cents, :recommended_seats, :factors, :explanation, 'pending', :priority, :due_date)
            RETURNING *
        """),
        {
            "org_id": org_id,
            "subscription_id": decision.subscription_id,
            "tool_id": decision.tool_id,
            "decision_type": decision.decision_type.value,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "risk_score": decision.risk_score,
            "savings_potential_cents": decision.savings_potential_cents,
            "recommended_seats": decision.recommended_seats,
            "factors": factors_json,
            "explanation": decision.explanation,
            "priority": decision.priority.value,
            "due_date": decision.due_date.isoformat() if decision.due_date else None,
        }
    )
    await db.commit()

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create decision")

    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "subscription_id": str(row.subscription_id) if row.subscription_id else None,
        "tool_id": str(row.tool_id) if row.tool_id else None,
        "decision_type": row.decision_type,
        "status": row.status,
        "priority": row.priority,
        "confidence": row.confidence,
        "risk_score": row.risk_score,
        "savings_potential_cents": row.savings_potential_cents,
        "explanation": row.explanation,
        "created_at": row.created_at,
    }


@router.get("", response_model=PaginatedResponse)
async def list_decisions(
    org_id: str,
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    decision_type: Optional[str] = None,
    priority: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all decisions."""
    conditions = ["d.org_id = :org_id"]
    params = {"org_id": org_id}

    if status:
        conditions.append("d.status = :status")
        params["status"] = status
    if decision_type:
        conditions.append("d.decision_type = :decision_type")
        params["decision_type"] = decision_type
    if priority:
        conditions.append("d.priority = :priority")
        params["priority"] = priority

    where_clause = " AND ".join(conditions)

    # Get total count
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM decisions d WHERE {where_clause}"),
        params
    )
    total = count_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    result = await db.execute(
        text(f"""
            SELECT d.*, st.name as tool_name, ts.plan_name as subscription_plan
            FROM decisions d
            LEFT JOIN saas_tools st ON d.tool_id = st.id
            LEFT JOIN tool_subscriptions ts ON d.subscription_id = ts.id
            WHERE {where_clause}
            ORDER BY d.created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params
    )

    items = []
    for row in result.fetchall():
        items.append({
            "id": str(row.id),
            "org_id": str(row.org_id),
            "subscription_id": str(row.subscription_id) if row.subscription_id else None,
            "tool_id": str(row.tool_id) if row.tool_id else None,
            "decision_type": row.decision_type,
            "status": row.status,
            "priority": row.priority,
            "confidence": row.confidence,
            "risk_score": row.risk_score,
            "savings_potential_cents": row.savings_potential_cents,
            "explanation": row.explanation,
            "tool_name": row.tool_name,
            "subscription_plan": row.subscription_plan,
            "created_at": row.created_at,
        })

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.get("/pending")
async def get_pending_decisions(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all pending decisions grouped by priority."""
    result = await db.execute(
        text("""
            SELECT d.*, st.name as tool_name, st.category as tool_category
            FROM decisions d
            LEFT JOIN saas_tools st ON d.tool_id = st.id
            WHERE d.org_id = :org_id AND d.status = 'pending'
            ORDER BY d.priority DESC
        """),
        {"org_id": org_id}
    )

    by_priority = {
        "urgent": [],
        "high": [],
        "normal": [],
        "low": []
    }

    total_savings = 0
    for row in result.fetchall():
        priority = row.priority or "normal"
        item = {
            "id": str(row.id),
            "decision_type": row.decision_type,
            "tool_name": row.tool_name,
            "category": row.tool_category,
            "savings_potential_cents": row.savings_potential_cents,
            "confidence": row.confidence,
        }
        by_priority.get(priority, by_priority["normal"]).append(item)
        total_savings += row.savings_potential_cents or 0

    return {
        "total_pending": sum(len(v) for v in by_priority.values()),
        "total_potential_savings_cents": total_savings,
        "by_priority": by_priority
    }


@router.get("/{decision_id}", response_model=DecisionWithDetails)
async def get_decision(
    org_id: str,
    decision_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get decision details."""
    result = await db.execute(
        text("""
            SELECT d.*, st.name as tool_name, ts.plan_name as subscription_plan, ou.name as decided_by_name
            FROM decisions d
            LEFT JOIN saas_tools st ON d.tool_id = st.id
            LEFT JOIN tool_subscriptions ts ON d.subscription_id = ts.id
            LEFT JOIN org_users ou ON d.decided_by = ou.id
            WHERE d.org_id = :org_id AND d.id = :decision_id
        """),
        {"org_id": org_id, "decision_id": decision_id}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Decision not found")

    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "subscription_id": str(row.subscription_id) if row.subscription_id else None,
        "tool_id": str(row.tool_id) if row.tool_id else None,
        "decision_type": row.decision_type,
        "status": row.status,
        "priority": row.priority,
        "confidence": row.confidence,
        "risk_score": row.risk_score,
        "savings_potential_cents": row.savings_potential_cents,
        "current_seats": row.current_seats,
        "recommended_seats": row.recommended_seats,
        "factors": row.factors,
        "explanation": row.explanation,
        "tool_name": row.tool_name,
        "subscription_plan": row.subscription_plan,
        "decided_by_name": row.decided_by_name,
        "decided_at": row.decided_at,
        "executed_at": row.executed_at,
        "created_at": row.created_at,
    }


@router.post("/{decision_id}/approve")
async def approve_decision(
    org_id: str,
    decision_id: str,
    approved_by: str,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Approve a decision."""
    existing = await db.execute(
        text("SELECT id, status FROM decisions WHERE org_id = :org_id AND id = :decision_id"),
        {"org_id": org_id, "decision_id": decision_id}
    )
    row = existing.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Decision not found")

    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Decision is not pending")

    await db.execute(
        text("""
            UPDATE decisions SET status = 'approved', decided_by = :approved_by, decided_at = NOW(), execution_notes = :notes
            WHERE id = :decision_id
        """),
        {"decision_id": decision_id, "approved_by": approved_by, "notes": notes}
    )
    await db.commit()

    return {"status": "approved", "decision_id": decision_id}


@router.post("/{decision_id}/reject")
async def reject_decision(
    org_id: str,
    decision_id: str,
    rejected_by: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Reject a decision."""
    existing = await db.execute(
        text("SELECT id, status FROM decisions WHERE org_id = :org_id AND id = :decision_id"),
        {"org_id": org_id, "decision_id": decision_id}
    )
    row = existing.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Decision not found")

    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Decision is not pending")

    notes = f"Rejected: {reason}" if reason else "Rejected"

    await db.execute(
        text("""
            UPDATE decisions SET status = 'rejected', decided_by = :rejected_by, decided_at = NOW(), execution_notes = :notes
            WHERE id = :decision_id
        """),
        {"decision_id": decision_id, "rejected_by": rejected_by, "notes": notes}
    )
    await db.commit()

    return {"status": "rejected", "decision_id": decision_id}


@router.post("/{decision_id}/execute")
async def execute_decision(
    org_id: str,
    decision_id: str,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Mark a decision as executed."""
    existing = await db.execute(
        text("SELECT id, status, decision_type, subscription_id, recommended_seats FROM decisions WHERE org_id = :org_id AND id = :decision_id"),
        {"org_id": org_id, "decision_id": decision_id}
    )
    row = existing.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Decision not found")

    if row.status != "approved":
        raise HTTPException(status_code=400, detail="Decision must be approved before execution")

    # Update decision status
    await db.execute(
        text("UPDATE decisions SET status = 'executed', executed_at = NOW(), execution_notes = :notes WHERE id = :decision_id"),
        {"decision_id": decision_id, "notes": notes}
    )

    # Apply decision to subscription if applicable
    if row.subscription_id:
        if row.decision_type == "cancel":
            await db.execute(
                text("UPDATE tool_subscriptions SET status = 'cancelled' WHERE id = :sub_id"),
                {"sub_id": row.subscription_id}
            )
        elif row.decision_type == "downsize" and row.recommended_seats:
            await db.execute(
                text("UPDATE tool_subscriptions SET paid_seats = :seats WHERE id = :sub_id"),
                {"sub_id": row.subscription_id, "seats": row.recommended_seats}
            )

    await db.commit()

    return {"status": "executed", "decision_id": decision_id}


@router.delete("/{decision_id}")
async def delete_decision(
    org_id: str,
    decision_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a decision."""
    existing = await db.execute(
        text("SELECT id FROM decisions WHERE org_id = :org_id AND id = :decision_id"),
        {"org_id": org_id, "decision_id": decision_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="Decision not found")

    await db.execute(
        text("DELETE FROM decisions WHERE id = :decision_id"),
        {"decision_id": decision_id}
    )
    await db.commit()

    return {"status": "deleted", "decision_id": decision_id}
