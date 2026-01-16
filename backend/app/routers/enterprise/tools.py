"""
Enterprise SaaS Tools API Router
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import re

from ...database import get_db
from ...models.enterprise_schemas import (
    SaaSTool,
    SaaSToolCreate,
    SaaSToolUpdate,
    SaaSToolWithStats,
    ToolAccess,
    ToolAccessCreate,
    ToolAccessUpdate,
    ToolDependency,
    ToolDependencyCreate,
    PaginatedResponse,
)

router = APIRouter(prefix="/organizations/{org_id}/tools", tags=["SaaS Tools"])


def normalize_name(name: str) -> str:
    """Normalize tool name for deduplication."""
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9]', '', name)
    return name


@router.post("", response_model=SaaSTool)
async def create_tool(
    org_id: str,
    tool: SaaSToolCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new SaaS tool."""
    normalized = tool.normalized_name or normalize_name(tool.name)

    # Check if tool already exists
    existing = await db.execute(
        text("SELECT id FROM saas_tools WHERE org_id = :org_id AND normalized_name = :normalized"),
        {"org_id": org_id, "normalized": normalized}
    )
    if existing.fetchone():
        raise HTTPException(status_code=400, detail="Tool already exists in organization")

    result = await db.execute(
        text("""
            INSERT INTO saas_tools (org_id, name, normalized_name, category, vendor_domain, vendor_url, description, discovery_source, status)
            VALUES (:org_id, :name, :normalized_name, :category, :vendor_domain, :vendor_url, :description, 'manual', 'active')
            RETURNING id, org_id, name, normalized_name, category, vendor_domain, vendor_url, logo_url, description, discovery_source, status, keystone_score, is_core, created_at, last_seen_at
        """),
        {
            "org_id": org_id,
            "name": tool.name,
            "normalized_name": normalized,
            "category": tool.category.value if tool.category else "other",
            "vendor_domain": tool.vendor_domain,
            "vendor_url": tool.vendor_url,
            "description": tool.description,
        }
    )
    await db.commit()

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create tool")

    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "name": row.name,
        "normalized_name": row.normalized_name,
        "category": row.category,
        "vendor_domain": row.vendor_domain,
        "vendor_url": row.vendor_url,
        "logo_url": row.logo_url,
        "description": row.description,
        "discovery_source": row.discovery_source,
        "status": row.status,
        "keystone_score": row.keystone_score,
        "is_core": row.is_core,
        "created_at": row.created_at,
        "last_seen_at": row.last_seen_at,
    }


@router.get("", response_model=PaginatedResponse)
async def list_tools(
    org_id: str,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all SaaS tools in organization."""
    # Build WHERE clause
    conditions = ["org_id = :org_id"]
    params = {"org_id": org_id}

    if search:
        conditions.append("(name ILIKE :search OR vendor_domain ILIKE :search)")
        params["search"] = f"%{search}%"
    if category:
        conditions.append("category = :category")
        params["category"] = category
    if status:
        conditions.append("status = :status")
        params["status"] = status

    where_clause = " AND ".join(conditions)

    # Get total count
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM saas_tools WHERE {where_clause}"),
        params
    )
    total = count_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    result = await db.execute(
        text(f"""
            SELECT id, org_id, name, normalized_name, category, vendor_domain, vendor_url, logo_url, description, discovery_source, status, keystone_score, is_core, created_at, last_seen_at
            FROM saas_tools
            WHERE {where_clause}
            ORDER BY name
            LIMIT :limit OFFSET :offset
        """),
        params
    )

    items = []
    for row in result.fetchall():
        items.append({
            "id": str(row.id),
            "org_id": str(row.org_id),
            "name": row.name,
            "normalized_name": row.normalized_name,
            "category": row.category,
            "vendor_domain": row.vendor_domain,
            "vendor_url": row.vendor_url,
            "logo_url": row.logo_url,
            "description": row.description,
            "discovery_source": row.discovery_source,
            "status": row.status,
            "keystone_score": row.keystone_score,
            "is_core": row.is_core,
            "created_at": row.created_at,
            "last_seen_at": row.last_seen_at,
        })

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.get("/categories")
async def list_categories(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get tool count by category."""
    result = await db.execute(
        text("SELECT category, COUNT(*) as count FROM saas_tools WHERE org_id = :org_id GROUP BY category"),
        {"org_id": org_id}
    )

    categories = {row.category or "other": row.count for row in result.fetchall()}
    return {"categories": categories}


@router.get("/{tool_id}", response_model=SaaSToolWithStats)
async def get_tool(
    org_id: str,
    tool_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get tool with usage stats."""
    result = await db.execute(
        text("""
            SELECT id, org_id, name, normalized_name, category, vendor_domain, vendor_url, logo_url, description, discovery_source, status, keystone_score, is_core, created_at, last_seen_at
            FROM saas_tools WHERE org_id = :org_id AND id = :tool_id
        """),
        {"org_id": org_id, "tool_id": tool_id}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Get user counts
    access_result = await db.execute(
        text("SELECT status FROM tool_access WHERE tool_id = :tool_id"),
        {"tool_id": tool_id}
    )
    access_rows = access_result.fetchall()
    total_users = len(access_rows)
    active_users = len([a for a in access_rows if a.status == "active"])

    # Get subscription cost
    sub_result = await db.execute(
        text("SELECT amount_cents, billing_cycle FROM tool_subscriptions WHERE tool_id = :tool_id AND status = 'active'"),
        {"tool_id": tool_id}
    )
    monthly_cost = 0
    for s in sub_result.fetchall():
        if s.billing_cycle == "yearly":
            monthly_cost += (s.amount_cents or 0) // 12
        elif s.billing_cycle == "quarterly":
            monthly_cost += (s.amount_cents or 0) // 3
        else:
            monthly_cost += s.amount_cents or 0

    # Get dependency count
    deps_result = await db.execute(
        text("SELECT COUNT(*) FROM tool_dependencies WHERE target_tool_id = :tool_id"),
        {"tool_id": tool_id}
    )
    dep_count = deps_result.scalar() or 0

    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "name": row.name,
        "normalized_name": row.normalized_name,
        "category": row.category,
        "vendor_domain": row.vendor_domain,
        "vendor_url": row.vendor_url,
        "logo_url": row.logo_url,
        "description": row.description,
        "discovery_source": row.discovery_source,
        "status": row.status,
        "keystone_score": row.keystone_score,
        "is_core": row.is_core,
        "created_at": row.created_at,
        "last_seen_at": row.last_seen_at,
        "active_users": active_users,
        "total_users": total_users,
        "monthly_cost": monthly_cost,
        "dependency_count": dep_count
    }


@router.patch("/{tool_id}", response_model=SaaSTool)
async def update_tool(
    org_id: str,
    tool_id: str,
    update: SaaSToolUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update tool."""
    existing = await db.execute(
        text("SELECT id FROM saas_tools WHERE org_id = :org_id AND id = :tool_id"),
        {"org_id": org_id, "tool_id": tool_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="Tool not found")

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    if "category" in update_data:
        update_data["category"] = update_data["category"].value if hasattr(update_data["category"], "value") else update_data["category"]
    if "status" in update_data:
        update_data["status"] = update_data["status"].value if hasattr(update_data["status"], "value") else update_data["status"]

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Build SET clause
    set_parts = []
    params = {"tool_id": tool_id}
    for key, value in update_data.items():
        set_parts.append(f"{key} = :{key}")
        params[key] = value

    set_clause = ", ".join(set_parts)

    result = await db.execute(
        text(f"""
            UPDATE saas_tools SET {set_clause}
            WHERE id = :tool_id
            RETURNING id, org_id, name, normalized_name, category, vendor_domain, vendor_url, logo_url, description, discovery_source, status, keystone_score, is_core, created_at, last_seen_at
        """),
        params
    )
    await db.commit()

    row = result.fetchone()
    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "name": row.name,
        "normalized_name": row.normalized_name,
        "category": row.category,
        "vendor_domain": row.vendor_domain,
        "vendor_url": row.vendor_url,
        "logo_url": row.logo_url,
        "description": row.description,
        "discovery_source": row.discovery_source,
        "status": row.status,
        "keystone_score": row.keystone_score,
        "is_core": row.is_core,
        "created_at": row.created_at,
        "last_seen_at": row.last_seen_at,
    }


@router.delete("/{tool_id}")
async def delete_tool(
    org_id: str,
    tool_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete tool."""
    existing = await db.execute(
        text("SELECT id FROM saas_tools WHERE org_id = :org_id AND id = :tool_id"),
        {"org_id": org_id, "tool_id": tool_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="Tool not found")

    await db.execute(
        text("DELETE FROM saas_tools WHERE id = :tool_id"),
        {"tool_id": tool_id}
    )
    await db.commit()

    return {"status": "deleted", "tool_id": tool_id}


# =============================================================================
# TOOL ACCESS
# =============================================================================

@router.get("/{tool_id}/access")
async def list_tool_access(
    org_id: str,
    tool_id: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all users with access to a tool."""
    conditions = ["ta.tool_id = :tool_id"]
    params = {"tool_id": tool_id}

    if status:
        conditions.append("ta.status = :status")
        params["status"] = status

    where_clause = " AND ".join(conditions)

    result = await db.execute(
        text(f"""
            SELECT ta.*, u.name as user_name, u.email as user_email, u.department as user_department, u.status as user_status
            FROM tool_access ta
            LEFT JOIN org_users u ON ta.user_id = u.id
            WHERE {where_clause}
        """),
        params
    )

    access = []
    for row in result.fetchall():
        access.append({
            "id": str(row.id),
            "tool_id": str(row.tool_id),
            "user_id": str(row.user_id),
            "access_level": row.access_level,
            "license_type": row.license_type,
            "status": row.status,
            "granted_at": row.granted_at,
            "last_active_at": row.last_active_at,
            "org_users": {
                "id": str(row.user_id),
                "name": row.user_name,
                "email": row.user_email,
                "department": row.user_department,
                "status": row.user_status,
            }
        })

    return {"access": access}


@router.post("/{tool_id}/access", response_model=ToolAccess)
async def grant_tool_access(
    org_id: str,
    tool_id: str,
    access: ToolAccessCreate,
    db: AsyncSession = Depends(get_db)
):
    """Grant user access to a tool."""
    # Verify tool exists
    tool = await db.execute(
        text("SELECT id FROM saas_tools WHERE org_id = :org_id AND id = :tool_id"),
        {"org_id": org_id, "tool_id": tool_id}
    )
    if not tool.fetchone():
        raise HTTPException(status_code=404, detail="Tool not found")

    # Check existing access
    existing = await db.execute(
        text("SELECT id FROM tool_access WHERE tool_id = :tool_id AND user_id = :user_id"),
        {"tool_id": tool_id, "user_id": access.user_id}
    )
    if existing.fetchone():
        raise HTTPException(status_code=400, detail="User already has access to this tool")

    result = await db.execute(
        text("""
            INSERT INTO tool_access (org_id, tool_id, user_id, access_level, license_type, granted_by, status)
            VALUES (:org_id, :tool_id, :user_id, :access_level, :license_type, :granted_by, 'active')
            RETURNING id, org_id, tool_id, user_id, access_level, license_type, granted_by, granted_at, last_active_at, status
        """),
        {
            "org_id": org_id,
            "tool_id": tool_id,
            "user_id": access.user_id,
            "access_level": access.access_level,
            "license_type": access.license_type,
            "granted_by": access.granted_by,
        }
    )
    await db.commit()

    row = result.fetchone()
    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "tool_id": str(row.tool_id),
        "user_id": str(row.user_id),
        "access_level": row.access_level,
        "license_type": row.license_type,
        "granted_by": str(row.granted_by) if row.granted_by else None,
        "granted_at": row.granted_at,
        "last_active_at": row.last_active_at,
        "status": row.status,
    }


@router.patch("/{tool_id}/access/{access_id}")
async def update_tool_access(
    org_id: str,
    tool_id: str,
    access_id: str,
    update: ToolAccessUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update tool access."""
    existing = await db.execute(
        text("SELECT id FROM tool_access WHERE id = :access_id"),
        {"access_id": access_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="Access record not found")

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Build SET clause
    set_parts = []
    params = {"access_id": access_id}
    for key, value in update_data.items():
        set_parts.append(f"{key} = :{key}")
        params[key] = value

    set_clause = ", ".join(set_parts)

    result = await db.execute(
        text(f"""
            UPDATE tool_access SET {set_clause}
            WHERE id = :access_id
            RETURNING id, org_id, tool_id, user_id, access_level, license_type, granted_by, granted_at, last_active_at, status
        """),
        params
    )
    await db.commit()

    row = result.fetchone()
    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "tool_id": str(row.tool_id),
        "user_id": str(row.user_id),
        "access_level": row.access_level,
        "license_type": row.license_type,
        "granted_by": str(row.granted_by) if row.granted_by else None,
        "granted_at": row.granted_at,
        "last_active_at": row.last_active_at,
        "status": row.status,
    }


@router.delete("/{tool_id}/access/{user_id}")
async def revoke_tool_access(
    org_id: str,
    tool_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Revoke user's access to a tool."""
    result = await db.execute(
        text("""
            UPDATE tool_access SET status = 'revoked'
            WHERE tool_id = :tool_id AND user_id = :user_id
            RETURNING id
        """),
        {"tool_id": tool_id, "user_id": user_id}
    )
    await db.commit()

    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Access record not found")

    return {"status": "revoked", "tool_id": tool_id, "user_id": user_id}


# =============================================================================
# TOOL DEPENDENCIES
# =============================================================================

@router.get("/{tool_id}/dependencies")
async def get_tool_dependencies(
    org_id: str,
    tool_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all dependencies for a tool (both incoming and outgoing)."""
    # Tools this tool depends on
    outgoing = await db.execute(
        text("""
            SELECT td.*, t.id as target_id, t.name as target_name, t.category as target_category
            FROM tool_dependencies td
            JOIN saas_tools t ON td.target_tool_id = t.id
            WHERE td.source_tool_id = :tool_id
        """),
        {"tool_id": tool_id}
    )

    depends_on = []
    for row in outgoing.fetchall():
        depends_on.append({
            "id": str(row.id),
            "source_tool_id": str(row.source_tool_id),
            "target_tool_id": str(row.target_tool_id),
            "dependency_type": row.dependency_type,
            "strength": row.strength,
            "description": row.description,
            "target": {
                "id": str(row.target_id),
                "name": row.target_name,
                "category": row.target_category,
            }
        })

    # Tools that depend on this tool
    incoming = await db.execute(
        text("""
            SELECT td.*, t.id as source_id, t.name as source_name, t.category as source_category
            FROM tool_dependencies td
            JOIN saas_tools t ON td.source_tool_id = t.id
            WHERE td.target_tool_id = :tool_id
        """),
        {"tool_id": tool_id}
    )

    depended_by = []
    for row in incoming.fetchall():
        depended_by.append({
            "id": str(row.id),
            "source_tool_id": str(row.source_tool_id),
            "target_tool_id": str(row.target_tool_id),
            "dependency_type": row.dependency_type,
            "strength": row.strength,
            "description": row.description,
            "source": {
                "id": str(row.source_id),
                "name": row.source_name,
                "category": row.source_category,
            }
        })

    return {
        "depends_on": depends_on,
        "depended_by": depended_by,
        "keystone_score": len(depended_by) / 10 if depended_by else 0
    }


@router.post("/{tool_id}/dependencies", response_model=ToolDependency)
async def create_dependency(
    org_id: str,
    tool_id: str,
    dep: ToolDependencyCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a dependency between tools."""
    result = await db.execute(
        text("""
            INSERT INTO tool_dependencies (org_id, source_tool_id, target_tool_id, dependency_type, strength, description, auto_discovered, verified)
            VALUES (:org_id, :source_tool_id, :target_tool_id, :dependency_type, :strength, :description, FALSE, TRUE)
            RETURNING id, org_id, source_tool_id, target_tool_id, dependency_type, strength, description, auto_discovered, verified, created_at
        """),
        {
            "org_id": org_id,
            "source_tool_id": dep.source_tool_id,
            "target_tool_id": dep.target_tool_id,
            "dependency_type": dep.dependency_type,
            "strength": dep.strength,
            "description": dep.description,
        }
    )
    await db.commit()

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create dependency")

    # Update keystone score
    incoming = await db.execute(
        text("SELECT COUNT(*) FROM tool_dependencies WHERE target_tool_id = :target_id"),
        {"target_id": dep.target_tool_id}
    )
    keystone_score = min((incoming.scalar() or 0) / 10, 1.0)
    await db.execute(
        text("UPDATE saas_tools SET keystone_score = :score WHERE id = :tool_id"),
        {"score": keystone_score, "tool_id": dep.target_tool_id}
    )
    await db.commit()

    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "source_tool_id": str(row.source_tool_id),
        "target_tool_id": str(row.target_tool_id),
        "dependency_type": row.dependency_type,
        "strength": row.strength,
        "description": row.description,
        "auto_discovered": row.auto_discovered,
        "verified": row.verified,
        "created_at": row.created_at,
    }


@router.delete("/{tool_id}/dependencies/{dep_id}")
async def delete_dependency(
    org_id: str,
    tool_id: str,
    dep_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a tool dependency."""
    existing = await db.execute(
        text("SELECT target_tool_id FROM tool_dependencies WHERE id = :dep_id"),
        {"dep_id": dep_id}
    )
    row = existing.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Dependency not found")

    target_id = str(row.target_tool_id)

    await db.execute(
        text("DELETE FROM tool_dependencies WHERE id = :dep_id"),
        {"dep_id": dep_id}
    )

    # Update keystone score
    incoming = await db.execute(
        text("SELECT COUNT(*) FROM tool_dependencies WHERE target_tool_id = :target_id"),
        {"target_id": target_id}
    )
    keystone_score = min((incoming.scalar() or 0) / 10, 1.0)
    await db.execute(
        text("UPDATE saas_tools SET keystone_score = :score WHERE id = :tool_id"),
        {"score": keystone_score, "tool_id": target_id}
    )
    await db.commit()

    return {"status": "deleted", "dep_id": dep_id}
