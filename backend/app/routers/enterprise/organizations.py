"""
Enterprise Organizations API Router
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import re

from ...database import get_db
from ...models.enterprise_schemas import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
    PaginatedResponse,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def normalize_domain(domain: str) -> str:
    """Normalize domain to lowercase without protocol."""
    domain = domain.lower().strip()
    domain = re.sub(r'^https?://', '', domain)
    domain = domain.split('/')[0]
    return domain


@router.post("", response_model=Organization)
async def create_organization(
    org: OrganizationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new organization."""
    normalized_domain = normalize_domain(org.domain)

    # Check if domain already exists
    result = await db.execute(
        text("SELECT id FROM organizations WHERE domain = :domain"),
        {"domain": normalized_domain}
    )
    existing = result.fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Organization with this domain already exists")

    # Insert new organization
    result = await db.execute(
        text("""
            INSERT INTO organizations (name, domain, plan, sso_provider, settings)
            VALUES (:name, :domain, :plan, :sso_provider, :settings)
            RETURNING id, name, domain, plan, sso_provider, settings, created_at, updated_at
        """),
        {
            "name": org.name,
            "domain": normalized_domain,
            "plan": org.plan.value,
            "sso_provider": org.sso_provider,
            "settings": "{}",
        }
    )
    await db.commit()

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create organization")

    return {
        "id": str(row.id),
        "name": row.name,
        "domain": row.domain,
        "plan": row.plan,
        "sso_provider": row.sso_provider,
        "settings": row.settings or {},
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("", response_model=PaginatedResponse)
async def list_organizations(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    plan: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all organizations with pagination."""
    # Build WHERE clause
    conditions = []
    params = {}

    if search:
        conditions.append("(name ILIKE :search OR domain ILIKE :search)")
        params["search"] = f"%{search}%"

    if plan:
        conditions.append("plan = :plan")
        params["plan"] = plan

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Get total count
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM organizations WHERE {where_clause}"),
        params
    )
    total = count_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    result = await db.execute(
        text(f"""
            SELECT id, name, domain, plan, sso_provider, settings, created_at, updated_at
            FROM organizations
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params
    )

    items = []
    for row in result.fetchall():
        items.append({
            "id": str(row.id),
            "name": row.name,
            "domain": row.domain,
            "plan": row.plan,
            "sso_provider": row.sso_provider,
            "settings": row.settings or {},
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        })

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.get("/{org_id}", response_model=Organization)
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get organization by ID."""
    result = await db.execute(
        text("""
            SELECT id, name, domain, plan, sso_provider, settings, created_at, updated_at
            FROM organizations WHERE id = :id
        """),
        {"id": org_id}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "id": str(row.id),
        "name": row.name,
        "domain": row.domain,
        "plan": row.plan,
        "sso_provider": row.sso_provider,
        "settings": row.settings or {},
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("/by-domain/{domain}", response_model=Organization)
async def get_organization_by_domain(
    domain: str,
    db: AsyncSession = Depends(get_db)
):
    """Get organization by domain."""
    normalized_domain = normalize_domain(domain)
    result = await db.execute(
        text("""
            SELECT id, name, domain, plan, sso_provider, settings, created_at, updated_at
            FROM organizations WHERE domain = :domain
        """),
        {"domain": normalized_domain}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "id": str(row.id),
        "name": row.name,
        "domain": row.domain,
        "plan": row.plan,
        "sso_provider": row.sso_provider,
        "settings": row.settings or {},
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.patch("/{org_id}", response_model=Organization)
async def update_organization(
    org_id: str,
    update: OrganizationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update organization."""
    # Check if org exists
    result = await db.execute(
        text("SELECT id FROM organizations WHERE id = :id"),
        {"id": org_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Organization not found")

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    if "plan" in update_data:
        update_data["plan"] = update_data["plan"].value if hasattr(update_data["plan"], "value") else update_data["plan"]

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Build SET clause
    set_parts = []
    params = {"id": org_id}
    for key, value in update_data.items():
        set_parts.append(f"{key} = :{key}")
        params[key] = value

    set_clause = ", ".join(set_parts)

    result = await db.execute(
        text(f"""
            UPDATE organizations SET {set_clause}, updated_at = NOW()
            WHERE id = :id
            RETURNING id, name, domain, plan, sso_provider, settings, created_at, updated_at
        """),
        params
    )
    await db.commit()

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to update organization")

    return {
        "id": str(row.id),
        "name": row.name,
        "domain": row.domain,
        "plan": row.plan,
        "sso_provider": row.sso_provider,
        "settings": row.settings or {},
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete organization and all related data."""
    # Check if org exists
    result = await db.execute(
        text("SELECT id FROM organizations WHERE id = :id"),
        {"id": org_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Organization not found")

    # Delete (cascade will handle related records)
    await db.execute(
        text("DELETE FROM organizations WHERE id = :id"),
        {"id": org_id}
    )
    await db.commit()

    return {"status": "deleted", "org_id": org_id}
