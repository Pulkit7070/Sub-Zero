"""
Enterprise Dashboard API Router
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date, timedelta

from ...database import get_db
from ...models.enterprise_schemas import DashboardStats

router = APIRouter(prefix="/organizations/{org_id}/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard overview statistics."""
    # Total tools
    tools_result = await db.execute(
        text("SELECT COUNT(*) FROM saas_tools WHERE org_id = :org_id AND status = 'active'"),
        {"org_id": org_id}
    )
    total_tools = tools_result.scalar() or 0

    # Active subscriptions and spending
    subs_result = await db.execute(
        text("SELECT amount_cents, billing_cycle, paid_seats, active_seats FROM tool_subscriptions WHERE org_id = :org_id AND status = 'active'"),
        {"org_id": org_id}
    )
    subs = subs_result.fetchall()

    active_subscriptions = len(subs)
    monthly_spend = 0
    total_paid_seats = 0
    total_active_seats = 0

    for s in subs:
        amount = s.amount_cents or 0
        cycle = s.billing_cycle
        if cycle == "yearly":
            monthly_spend += amount // 12
        elif cycle == "quarterly":
            monthly_spend += amount // 3
        else:
            monthly_spend += amount
        total_paid_seats += s.paid_seats or 0
        total_active_seats += s.active_seats or 0

    # Total users
    users_result = await db.execute(
        text("SELECT COUNT(*) FROM org_users WHERE org_id = :org_id AND status = 'active'"),
        {"org_id": org_id}
    )
    total_users = users_result.scalar() or 0

    # Pending decisions
    decisions_result = await db.execute(
        text("SELECT savings_potential_cents FROM decisions WHERE org_id = :org_id AND status = 'pending'"),
        {"org_id": org_id}
    )
    decisions = decisions_result.fetchall()
    pending_decisions = len(decisions)
    potential_savings = sum(d.savings_potential_cents or 0 for d in decisions)

    # Tools under review
    review_result = await db.execute(
        text("SELECT COUNT(*) FROM saas_tools WHERE org_id = :org_id AND status = 'under_review'"),
        {"org_id": org_id}
    )
    tools_under_review = review_result.scalar() or 0

    avg_utilization = total_active_seats / total_paid_seats if total_paid_seats > 0 else 0

    return DashboardStats(
        total_tools=total_tools,
        active_subscriptions=active_subscriptions,
        total_users=total_users,
        monthly_spend_cents=monthly_spend,
        annual_spend_cents=monthly_spend * 12,
        potential_savings_cents=potential_savings,
        pending_decisions=pending_decisions,
        tools_under_review=tools_under_review,
        avg_utilization=round(avg_utilization, 2)
    )


@router.get("/quick-wins")
async def get_quick_wins(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get quick optimization opportunities."""
    quick_wins = []

    # Zero usage subscriptions
    zero_result = await db.execute(
        text("""
            SELECT ts.id, ts.amount_cents, ts.billing_cycle, st.name
            FROM tool_subscriptions ts
            LEFT JOIN saas_tools st ON ts.tool_id = st.id
            WHERE ts.org_id = :org_id AND ts.status = 'active' AND ts.active_seats = 0
        """),
        {"org_id": org_id}
    )
    for s in zero_result.fetchall():
        amount = s.amount_cents or 0
        cycle = s.billing_cycle
        annual = amount * 12 if cycle == "monthly" else (amount * 4 if cycle == "quarterly" else amount)
        quick_wins.append({
            "type": "zero_usage",
            "subscription_id": str(s.id),
            "tool_name": s.name,
            "potential_annual_savings_cents": annual,
            "action": "Consider cancelling - no active users",
            "priority": "high"
        })

    return {"quick_wins": quick_wins, "total_count": len(quick_wins)}


@router.get("/utilization-report")
async def get_utilization_report(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get utilization report."""
    result = await db.execute(
        text("""
            SELECT ts.id, ts.paid_seats, ts.active_seats, ts.amount_cents, ts.billing_cycle, st.name, st.category
            FROM tool_subscriptions ts
            LEFT JOIN saas_tools st ON ts.tool_id = st.id
            WHERE ts.org_id = :org_id AND ts.status = 'active'
        """),
        {"org_id": org_id}
    )

    report = {"healthy": [], "moderate": [], "underutilized": [], "critical": []}
    total_waste = 0

    for s in result.fetchall():
        paid = s.paid_seats or 0
        active = s.active_seats or 0
        if paid == 0:
            continue

        utilization = active / paid
        amount = s.amount_cents or 0
        cycle = s.billing_cycle
        monthly = amount // 12 if cycle == "yearly" else (amount // 3 if cycle == "quarterly" else amount)
        unused_seats = paid - active
        waste_per_seat = monthly / paid if paid > 0 else 0
        monthly_waste = int(unused_seats * waste_per_seat)

        item = {
            "subscription_id": str(s.id),
            "tool_name": s.name,
            "category": s.category,
            "paid_seats": paid,
            "active_seats": active,
            "utilization": round(utilization, 2),
            "monthly_cost_cents": monthly,
            "monthly_waste_cents": monthly_waste
        }

        if utilization >= 0.7:
            report["healthy"].append(item)
        elif utilization >= 0.5:
            report["moderate"].append(item)
        elif utilization >= 0.3:
            report["underutilized"].append(item)
            total_waste += monthly_waste
        else:
            report["critical"].append(item)
            total_waste += monthly_waste

    return {
        "report": report,
        "summary": {
            "healthy_count": len(report["healthy"]),
            "moderate_count": len(report["moderate"]),
            "underutilized_count": len(report["underutilized"]),
            "critical_count": len(report["critical"]),
            "total_monthly_waste_cents": total_waste,
        }
    }
