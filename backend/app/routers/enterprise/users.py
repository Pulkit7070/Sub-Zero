"""
Enterprise Users API Router
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from datetime import datetime

from ...database import get_db
from ...models.enterprise_schemas import (
    OrgUser,
    OrgUserCreate,
    OrgUserUpdate,
    PaginatedResponse,
)

router = APIRouter(prefix="/organizations/{org_id}/users", tags=["Organization Users"])


@router.post("", response_model=OrgUser)
async def create_user(
    org_id: str,
    user: OrgUserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new user in an organization."""
    # Verify org exists
    org_result = await db.execute(
        text("SELECT id FROM organizations WHERE id = :id"),
        {"id": org_id}
    )
    if not org_result.fetchone():
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check if user already exists
    existing = await db.execute(
        text("SELECT id FROM org_users WHERE org_id = :org_id AND email = :email"),
        {"org_id": org_id, "email": user.email}
    )
    if existing.fetchone():
        raise HTTPException(status_code=400, detail="User with this email already exists in organization")

    result = await db.execute(
        text("""
            INSERT INTO org_users (org_id, email, name, department, job_title, role, manager_id, status)
            VALUES (:org_id, :email, :name, :department, :job_title, :role, :manager_id, 'active')
            RETURNING id, org_id, email, name, department, job_title, role, manager_id, status, created_at, offboarded_at
        """),
        {
            "org_id": org_id,
            "email": user.email,
            "name": user.name,
            "department": user.department,
            "job_title": user.job_title,
            "role": user.role.value,
            "manager_id": user.manager_id,
        }
    )
    await db.commit()

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create user")

    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "email": row.email,
        "name": row.name,
        "department": row.department,
        "job_title": row.job_title,
        "role": row.role,
        "manager_id": str(row.manager_id) if row.manager_id else None,
        "status": row.status,
        "created_at": row.created_at,
        "offboarded_at": row.offboarded_at,
    }


@router.get("", response_model=PaginatedResponse)
async def list_users(
    org_id: str,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    department: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = Query(None, description="Filter by status: active, inactive, offboarded"),
    db: AsyncSession = Depends(get_db)
):
    """List all users in an organization."""
    # Build WHERE clause
    conditions = ["org_id = :org_id"]
    params = {"org_id": org_id}

    if search:
        conditions.append("(name ILIKE :search OR email ILIKE :search)")
        params["search"] = f"%{search}%"
    if department:
        conditions.append("department = :department")
        params["department"] = department
    if role:
        conditions.append("role = :role")
        params["role"] = role
    if status:
        conditions.append("status = :status")
        params["status"] = status

    where_clause = " AND ".join(conditions)

    # Get total count
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM org_users WHERE {where_clause}"),
        params
    )
    total = count_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    result = await db.execute(
        text(f"""
            SELECT id, org_id, email, name, department, job_title, role, manager_id, status, created_at, offboarded_at
            FROM org_users
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
            "email": row.email,
            "name": row.name,
            "department": row.department,
            "job_title": row.job_title,
            "role": row.role,
            "manager_id": str(row.manager_id) if row.manager_id else None,
            "status": row.status,
            "created_at": row.created_at,
            "offboarded_at": row.offboarded_at,
        })

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.get("/departments")
async def list_departments(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get list of unique departments in organization."""
    result = await db.execute(
        text("SELECT DISTINCT department FROM org_users WHERE org_id = :org_id AND department IS NOT NULL"),
        {"org_id": org_id}
    )

    departments = sorted([row.department for row in result.fetchall()])
    return {"departments": departments}


@router.get("/{user_id}", response_model=OrgUser)
async def get_user(
    org_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID."""
    result = await db.execute(
        text("""
            SELECT id, org_id, email, name, department, job_title, role, manager_id, status, created_at, offboarded_at
            FROM org_users WHERE org_id = :org_id AND id = :user_id
        """),
        {"org_id": org_id, "user_id": user_id}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "email": row.email,
        "name": row.name,
        "department": row.department,
        "job_title": row.job_title,
        "role": row.role,
        "manager_id": str(row.manager_id) if row.manager_id else None,
        "status": row.status,
        "created_at": row.created_at,
        "offboarded_at": row.offboarded_at,
    }


@router.get("/{user_id}/tools")
async def get_user_tools(
    org_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all tools a user has access to."""
    result = await db.execute(
        text("""
            SELECT ta.*, st.id as tool_id, st.name as tool_name, st.category, st.logo_url
            FROM tool_access ta
            JOIN saas_tools st ON ta.tool_id = st.id
            WHERE ta.org_id = :org_id AND ta.user_id = :user_id AND ta.status = 'active'
        """),
        {"org_id": org_id, "user_id": user_id}
    )

    tools = []
    for row in result.fetchall():
        tools.append({
            "id": str(row.id),
            "tool_id": str(row.tool_id),
            "tool_name": row.tool_name,
            "category": row.category,
            "logo_url": row.logo_url,
            "access_level": row.access_level,
            "granted_at": row.granted_at,
        })

    return {"tools": tools}


@router.get("/{user_id}/direct-reports")
async def get_direct_reports(
    org_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all direct reports for a manager."""
    result = await db.execute(
        text("""
            SELECT id, org_id, email, name, department, job_title, role, manager_id, status, created_at, offboarded_at
            FROM org_users WHERE org_id = :org_id AND manager_id = :user_id
        """),
        {"org_id": org_id, "user_id": user_id}
    )

    direct_reports = []
    for row in result.fetchall():
        direct_reports.append({
            "id": str(row.id),
            "org_id": str(row.org_id),
            "email": row.email,
            "name": row.name,
            "department": row.department,
            "job_title": row.job_title,
            "role": row.role,
            "manager_id": str(row.manager_id) if row.manager_id else None,
            "status": row.status,
            "created_at": row.created_at,
            "offboarded_at": row.offboarded_at,
        })

    return {"direct_reports": direct_reports}


@router.patch("/{user_id}", response_model=OrgUser)
async def update_user(
    org_id: str,
    user_id: str,
    update: OrgUserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update user."""
    existing = await db.execute(
        text("SELECT id FROM org_users WHERE org_id = :org_id AND id = :user_id"),
        {"org_id": org_id, "user_id": user_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    if "role" in update_data:
        update_data["role"] = update_data["role"].value if hasattr(update_data["role"], "value") else update_data["role"]
    if "status" in update_data:
        update_data["status"] = update_data["status"].value if hasattr(update_data["status"], "value") else update_data["status"]

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Build SET clause
    set_parts = []
    params = {"user_id": user_id}
    for key, value in update_data.items():
        set_parts.append(f"{key} = :{key}")
        params[key] = value

    set_clause = ", ".join(set_parts)

    result = await db.execute(
        text(f"""
            UPDATE org_users SET {set_clause}
            WHERE id = :user_id
            RETURNING id, org_id, email, name, department, job_title, role, manager_id, status, created_at, offboarded_at
        """),
        params
    )
    await db.commit()

    row = result.fetchone()
    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "email": row.email,
        "name": row.name,
        "department": row.department,
        "job_title": row.job_title,
        "role": row.role,
        "manager_id": str(row.manager_id) if row.manager_id else None,
        "status": row.status,
        "created_at": row.created_at,
        "offboarded_at": row.offboarded_at,
    }


@router.post("/{user_id}/offboard")
async def offboard_user(
    org_id: str,
    user_id: str,
    revoke_access: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Offboard a user - marks as offboarded and optionally revokes tool access."""
    existing = await db.execute(
        text("SELECT id FROM org_users WHERE org_id = :org_id AND id = :user_id"),
        {"org_id": org_id, "user_id": user_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    # Update user status
    await db.execute(
        text("""
            UPDATE org_users SET status = 'offboarded', offboarded_at = NOW()
            WHERE id = :user_id
        """),
        {"user_id": user_id}
    )

    revoked_count = 0
    if revoke_access:
        # Revoke all tool access
        result = await db.execute(
            text("UPDATE tool_access SET status = 'revoked' WHERE user_id = :user_id RETURNING id"),
            {"user_id": user_id}
        )
        revoked_count = len(result.fetchall())

    await db.commit()

    return {
        "status": "offboarded",
        "user_id": user_id,
        "access_revoked": revoked_count
    }


@router.delete("/{user_id}")
async def delete_user(
    org_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete user from organization."""
    existing = await db.execute(
        text("SELECT id FROM org_users WHERE org_id = :org_id AND id = :user_id"),
        {"org_id": org_id, "user_id": user_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute(
        text("DELETE FROM org_users WHERE id = :user_id"),
        {"user_id": user_id}
    )
    await db.commit()

    return {"status": "deleted", "user_id": user_id}


@router.post("/bulk-import")
async def bulk_import_users(
    org_id: str,
    users: list[OrgUserCreate],
    db: AsyncSession = Depends(get_db)
):
    """Bulk import users from CSV/API."""
    # Verify org exists
    org_result = await db.execute(
        text("SELECT id FROM organizations WHERE id = :id"),
        {"id": org_id}
    )
    if not org_result.fetchone():
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get existing emails
    existing = await db.execute(
        text("SELECT email FROM org_users WHERE org_id = :org_id"),
        {"org_id": org_id}
    )
    existing_emails = {row.email.lower() for row in existing.fetchall()}

    created = []
    skipped = []

    for user in users:
        if user.email.lower() in existing_emails:
            skipped.append({"email": user.email, "reason": "already exists"})
            continue

        result = await db.execute(
            text("""
                INSERT INTO org_users (org_id, email, name, department, job_title, role, status)
                VALUES (:org_id, :email, :name, :department, :job_title, :role, 'active')
                RETURNING id, org_id, email, name, department, job_title, role, manager_id, status, created_at, offboarded_at
            """),
            {
                "org_id": org_id,
                "email": user.email,
                "name": user.name,
                "department": user.department,
                "job_title": user.job_title,
                "role": user.role.value,
            }
        )
        row = result.fetchone()
        if row:
            created.append({
                "id": str(row.id),
                "email": row.email,
                "name": row.name,
            })
            existing_emails.add(user.email.lower())

    await db.commit()

    return {
        "created_count": len(created),
        "skipped_count": len(skipped),
        "created": created,
        "skipped": skipped
    }
