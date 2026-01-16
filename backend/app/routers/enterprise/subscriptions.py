"""
Enterprise Subscriptions API Router
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from datetime import date, timedelta

from ...database import get_db
from ...models.enterprise_schemas import (
    ToolSubscription,
    ToolSubscriptionCreate,
    ToolSubscriptionUpdate,
    ToolSubscriptionWithDetails,
    PaginatedResponse,
)

router = APIRouter(prefix="/organizations/{org_id}/subscriptions", tags=["Subscriptions"])


@router.post("", response_model=ToolSubscription)
async def create_subscription(
    org_id: str,
    sub: ToolSubscriptionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new subscription."""
    # Verify tool exists
    tool = await db.execute(
        text("SELECT id FROM saas_tools WHERE org_id = :org_id AND id = :tool_id"),
        {"org_id": org_id, "tool_id": sub.tool_id}
    )
    if not tool.fetchone():
        raise HTTPException(status_code=404, detail="Tool not found")

    result = await db.execute(
        text("""
            INSERT INTO tool_subscriptions (org_id, tool_id, plan_name, billing_cycle, amount_cents, currency, paid_seats, renewal_date, auto_renew, owner_id, department, cost_center, status, billing_source)
            VALUES (:org_id, :tool_id, :plan_name, :billing_cycle, :amount_cents, :currency, :paid_seats, :renewal_date, :auto_renew, :owner_id, :department, :cost_center, 'active', 'manual')
            RETURNING *
        """),
        {
            "org_id": org_id,
            "tool_id": sub.tool_id,
            "plan_name": sub.plan_name,
            "billing_cycle": sub.billing_cycle.value,
            "amount_cents": sub.amount_cents,
            "currency": sub.currency,
            "paid_seats": sub.paid_seats,
            "renewal_date": sub.renewal_date.isoformat() if sub.renewal_date else None,
            "auto_renew": sub.auto_renew,
            "owner_id": sub.owner_id,
            "department": sub.department,
            "cost_center": sub.cost_center,
        }
    )
    await db.commit()

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create subscription")

    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "tool_id": str(row.tool_id),
        "plan_name": row.plan_name,
        "billing_cycle": row.billing_cycle,
        "amount_cents": row.amount_cents,
        "currency": row.currency,
        "paid_seats": row.paid_seats,
        "active_seats": row.active_seats,
        "renewal_date": row.renewal_date,
        "auto_renew": row.auto_renew,
        "owner_id": str(row.owner_id) if row.owner_id else None,
        "department": row.department,
        "cost_center": row.cost_center,
        "status": row.status,
        "billing_source": row.billing_source,
        "created_at": row.created_at,
    }


@router.get("", response_model=PaginatedResponse)
async def list_subscriptions(
    org_id: str,
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    department: Optional[str] = None,
    owner_id: Optional[str] = None,
    renewal_within_days: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all subscriptions with filters."""
    conditions = ["ts.org_id = :org_id"]
    params = {"org_id": org_id}

    if status:
        conditions.append("ts.status = :status")
        params["status"] = status
    if department:
        conditions.append("ts.department = :department")
        params["department"] = department
    if owner_id:
        conditions.append("ts.owner_id = :owner_id")
        params["owner_id"] = owner_id
    if renewal_within_days:
        cutoff = (date.today() + timedelta(days=renewal_within_days)).isoformat()
        conditions.append("ts.renewal_date <= :cutoff AND ts.renewal_date >= :today")
        params["cutoff"] = cutoff
        params["today"] = date.today().isoformat()

    where_clause = " AND ".join(conditions)

    # Get total count
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM tool_subscriptions ts WHERE {where_clause}"),
        params
    )
    total = count_result.scalar() or 0

    # Get paginated results with joins
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    result = await db.execute(
        text(f"""
            SELECT ts.*, st.name as tool_name, st.category as tool_category, ou.name as owner_name, ou.status as owner_status
            FROM tool_subscriptions ts
            LEFT JOIN saas_tools st ON ts.tool_id = st.id
            LEFT JOIN org_users ou ON ts.owner_id = ou.id
            WHERE {where_clause}
            ORDER BY ts.renewal_date
            LIMIT :limit OFFSET :offset
        """),
        params
    )

    items = []
    for row in result.fetchall():
        items.append({
            "id": str(row.id),
            "org_id": str(row.org_id),
            "tool_id": str(row.tool_id),
            "plan_name": row.plan_name,
            "billing_cycle": row.billing_cycle,
            "amount_cents": row.amount_cents,
            "currency": row.currency,
            "paid_seats": row.paid_seats,
            "active_seats": row.active_seats,
            "renewal_date": row.renewal_date,
            "auto_renew": row.auto_renew,
            "owner_id": str(row.owner_id) if row.owner_id else None,
            "department": row.department,
            "cost_center": row.cost_center,
            "status": row.status,
            "tool_name": row.tool_name,
            "tool_category": row.tool_category,
            "owner_name": row.owner_name,
            "owner_status": row.owner_status,
        })

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.get("/upcoming-renewals")
async def get_upcoming_renewals(
    org_id: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get subscriptions with upcoming renewals."""
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    today = date.today().isoformat()

    result = await db.execute(
        text("""
            SELECT ts.id, ts.tool_id, ts.renewal_date, ts.amount_cents, ts.billing_cycle, st.name as tool_name
            FROM tool_subscriptions ts
            LEFT JOIN saas_tools st ON ts.tool_id = st.id
            WHERE ts.org_id = :org_id AND ts.status = 'active' AND ts.renewal_date <= :cutoff AND ts.renewal_date >= :today
            ORDER BY ts.renewal_date
        """),
        {"org_id": org_id, "cutoff": cutoff, "today": today}
    )

    renewals = []
    for row in result.fetchall():
        renewal_date = row.renewal_date if row.renewal_date else None
        days_until = (renewal_date - date.today()).days if renewal_date else 999

        urgency = "ok"
        if days_until <= 7:
            urgency = "urgent"
        elif days_until <= 30:
            urgency = "soon"
        elif days_until <= 60:
            urgency = "upcoming"

        renewals.append({
            "subscription_id": str(row.id),
            "tool_id": str(row.tool_id),
            "tool_name": row.tool_name or "Unknown",
            "renewal_date": renewal_date.isoformat() if renewal_date else None,
            "amount_cents": row.amount_cents,
            "days_until": days_until,
            "urgency": urgency
        })

    return {"renewals": renewals}


@router.get("/spend-summary")
async def get_spend_summary(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get spending summary by category and department."""
    result = await db.execute(
        text("""
            SELECT ts.amount_cents, ts.billing_cycle, ts.department, st.category
            FROM tool_subscriptions ts
            LEFT JOIN saas_tools st ON ts.tool_id = st.id
            WHERE ts.org_id = :org_id AND ts.status = 'active'
        """),
        {"org_id": org_id}
    )

    by_category = {}
    by_department = {}
    total_monthly = 0

    for row in result.fetchall():
        amount = row.amount_cents or 0
        cycle = row.billing_cycle

        # Convert to monthly
        if cycle == "yearly":
            monthly = amount // 12
        elif cycle == "quarterly":
            monthly = amount // 3
        else:
            monthly = amount

        total_monthly += monthly

        # By category
        cat = row.category or "other"
        if cat not in by_category:
            by_category[cat] = {"amount_cents": 0, "count": 0}
        by_category[cat]["amount_cents"] += monthly
        by_category[cat]["count"] += 1

        # By department
        dept = row.department or "unassigned"
        if dept not in by_department:
            by_department[dept] = {"amount_cents": 0, "count": 0}
        by_department[dept]["amount_cents"] += monthly
        by_department[dept]["count"] += 1

    return {
        "total_monthly_cents": total_monthly,
        "total_annual_cents": total_monthly * 12,
        "by_category": by_category,
        "by_department": by_department
    }


@router.get("/{sub_id}", response_model=ToolSubscriptionWithDetails)
async def get_subscription(
    org_id: str,
    sub_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get subscription details."""
    result = await db.execute(
        text("""
            SELECT ts.*, st.name as tool_name, st.category as tool_category, ou.name as owner_name, ou.status as owner_status
            FROM tool_subscriptions ts
            LEFT JOIN saas_tools st ON ts.tool_id = st.id
            LEFT JOIN org_users ou ON ts.owner_id = ou.id
            WHERE ts.org_id = :org_id AND ts.id = :sub_id
        """),
        {"org_id": org_id, "sub_id": sub_id}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Calculate utilization
    utilization = 0
    if row.paid_seats and row.paid_seats > 0:
        utilization = (row.active_seats or 0) / row.paid_seats

    # Days until renewal
    days_until = None
    if row.renewal_date:
        days_until = (row.renewal_date - date.today()).days

    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "tool_id": str(row.tool_id),
        "plan_name": row.plan_name,
        "billing_cycle": row.billing_cycle,
        "amount_cents": row.amount_cents,
        "currency": row.currency,
        "paid_seats": row.paid_seats,
        "active_seats": row.active_seats,
        "renewal_date": row.renewal_date,
        "auto_renew": row.auto_renew,
        "owner_id": str(row.owner_id) if row.owner_id else None,
        "department": row.department,
        "cost_center": row.cost_center,
        "status": row.status,
        "tool_name": row.tool_name or "Unknown",
        "owner_name": row.owner_name,
        "owner_status": row.owner_status,
        "utilization_rate": utilization,
        "days_until_renewal": days_until
    }


@router.patch("/{sub_id}", response_model=ToolSubscription)
async def update_subscription(
    org_id: str,
    sub_id: str,
    update: ToolSubscriptionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update subscription."""
    existing = await db.execute(
        text("SELECT id FROM tool_subscriptions WHERE org_id = :org_id AND id = :sub_id"),
        {"org_id": org_id, "sub_id": sub_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="Subscription not found")

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    if "billing_cycle" in update_data:
        update_data["billing_cycle"] = update_data["billing_cycle"].value if hasattr(update_data["billing_cycle"], "value") else update_data["billing_cycle"]
    if "status" in update_data:
        update_data["status"] = update_data["status"].value if hasattr(update_data["status"], "value") else update_data["status"]
    if "renewal_date" in update_data and update_data["renewal_date"]:
        update_data["renewal_date"] = update_data["renewal_date"].isoformat()
    if "contract_end_date" in update_data and update_data["contract_end_date"]:
        update_data["contract_end_date"] = update_data["contract_end_date"].isoformat()

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Build SET clause
    set_parts = []
    params = {"sub_id": sub_id}
    for key, value in update_data.items():
        set_parts.append(f"{key} = :{key}")
        params[key] = value

    set_clause = ", ".join(set_parts)

    result = await db.execute(
        text(f"""
            UPDATE tool_subscriptions SET {set_clause}
            WHERE id = :sub_id
            RETURNING *
        """),
        params
    )
    await db.commit()

    row = result.fetchone()
    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "tool_id": str(row.tool_id),
        "plan_name": row.plan_name,
        "billing_cycle": row.billing_cycle,
        "amount_cents": row.amount_cents,
        "currency": row.currency,
        "paid_seats": row.paid_seats,
        "active_seats": row.active_seats,
        "renewal_date": row.renewal_date,
        "auto_renew": row.auto_renew,
        "owner_id": str(row.owner_id) if row.owner_id else None,
        "department": row.department,
        "cost_center": row.cost_center,
        "status": row.status,
    }


@router.post("/{sub_id}/cancel")
async def cancel_subscription(
    org_id: str,
    sub_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a subscription."""
    existing = await db.execute(
        text("SELECT id FROM tool_subscriptions WHERE org_id = :org_id AND id = :sub_id"),
        {"org_id": org_id, "sub_id": sub_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="Subscription not found")

    notes = f"Cancelled. Reason: {reason}" if reason else "Cancelled by user"

    await db.execute(
        text("UPDATE tool_subscriptions SET status = 'cancelled', notes = :notes WHERE id = :sub_id"),
        {"sub_id": sub_id, "notes": notes}
    )
    await db.commit()

    return {"status": "cancelled", "subscription_id": sub_id}


@router.delete("/{sub_id}")
async def delete_subscription(
    org_id: str,
    sub_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete subscription."""
    existing = await db.execute(
        text("SELECT id FROM tool_subscriptions WHERE org_id = :org_id AND id = :sub_id"),
        {"org_id": org_id, "sub_id": sub_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="Subscription not found")

    await db.execute(
        text("DELETE FROM tool_subscriptions WHERE id = :sub_id"),
        {"sub_id": sub_id}
    )
    await db.commit()

    return {"status": "deleted", "subscription_id": sub_id}
