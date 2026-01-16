"""
Enterprise Integrations API Router (SSO, Directory Sync)
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from datetime import datetime

from ...database import get_db
from ...models.enterprise_schemas import (
    Integration,
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationProvider,
)

router = APIRouter(prefix="/organizations/{org_id}/integrations", tags=["Integrations"])


@router.get("")
async def list_integrations(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all connected integrations."""
    result = await db.execute(
        text("""
            SELECT id, provider, status, last_sync_at, sync_status, sync_error, created_at, updated_at
            FROM org_integrations WHERE org_id = :org_id
        """),
        {"org_id": org_id}
    )

    integrations = []
    for row in result.fetchall():
        integrations.append({
            "id": str(row.id),
            "provider": row.provider,
            "status": row.status,
            "last_sync_at": row.last_sync_at,
            "sync_status": row.sync_status,
            "sync_error": row.sync_error,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        })

    return {"integrations": integrations}


@router.get("/available")
async def list_available_integrations():
    """List all available integration providers."""
    return {
        "providers": [
            {
                "id": "google_workspace",
                "name": "Google Workspace",
                "description": "Sync users and discover apps from Google Workspace",
                "scopes": [
                    "https://www.googleapis.com/auth/admin.directory.user.readonly",
                    "https://www.googleapis.com/auth/admin.directory.group.readonly",
                ],
                "features": ["user_sync", "app_discovery", "sso"]
            },
            {
                "id": "microsoft_entra",
                "name": "Microsoft Entra ID (Azure AD)",
                "description": "Sync users and discover apps from Microsoft 365",
                "scopes": ["User.Read.All", "Directory.Read.All", "Application.Read.All"],
                "features": ["user_sync", "app_discovery", "sso"]
            },
            {
                "id": "okta",
                "name": "Okta",
                "description": "Sync users and discover apps from Okta",
                "scopes": ["okta.users.read", "okta.apps.read", "okta.groups.read"],
                "features": ["user_sync", "app_discovery", "sso"]
            },
            {
                "id": "slack",
                "name": "Slack",
                "description": "Discover Slack apps and integrations",
                "scopes": ["users:read", "team:read", "apps:read"],
                "features": ["app_discovery", "notifications"]
            }
        ]
    }


@router.post("")
async def create_integration(
    org_id: str,
    integration: IntegrationCreate,
    connected_by: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Connect a new integration."""
    # Check if already connected
    existing = await db.execute(
        text("SELECT id FROM org_integrations WHERE org_id = :org_id AND provider = :provider"),
        {"org_id": org_id, "provider": integration.provider.value}
    )
    if existing.fetchone():
        raise HTTPException(status_code=400, detail="Integration already connected")

    # In production, encrypt tokens before storing
    result = await db.execute(
        text("""
            INSERT INTO org_integrations (org_id, provider, status, access_token_encrypted, refresh_token_encrypted, scopes, connected_by, config, metadata)
            VALUES (:org_id, :provider, 'connected', :access_token, :refresh_token, :scopes, :connected_by, '{}', '{}')
            RETURNING id, provider, status, created_at
        """),
        {
            "org_id": org_id,
            "provider": integration.provider.value,
            "access_token": integration.access_token,  # Should encrypt!
            "refresh_token": integration.refresh_token,
            "scopes": integration.scopes,
            "connected_by": connected_by,
        }
    )
    await db.commit()

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create integration")

    return {
        "id": str(row.id),
        "provider": row.provider,
        "status": row.status,
        "created_at": row.created_at
    }


@router.get("/{integration_id}")
async def get_integration(
    org_id: str,
    integration_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get integration details."""
    result = await db.execute(
        text("""
            SELECT id, provider, status, scopes, last_sync_at, sync_status, sync_error, config, metadata, created_at, updated_at
            FROM org_integrations WHERE org_id = :org_id AND id = :integration_id
        """),
        {"org_id": org_id, "integration_id": integration_id}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    return {
        "id": str(row.id),
        "provider": row.provider,
        "status": row.status,
        "scopes": row.scopes,
        "last_sync_at": row.last_sync_at,
        "sync_status": row.sync_status,
        "sync_error": row.sync_error,
        "config": row.config,
        "metadata": row.metadata,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.post("/{integration_id}/sync")
async def trigger_sync(
    org_id: str,
    integration_id: str,
    sync_type: str = "incremental",
    db: AsyncSession = Depends(get_db)
):
    """Trigger a sync for an integration."""
    # Get integration
    integration = await db.execute(
        text("SELECT * FROM org_integrations WHERE org_id = :org_id AND id = :integration_id"),
        {"org_id": org_id, "integration_id": integration_id}
    )
    int_data = integration.fetchone()
    if not int_data:
        raise HTTPException(status_code=404, detail="Integration not found")

    provider = int_data.provider

    # Update sync status
    await db.execute(
        text("UPDATE org_integrations SET sync_status = 'running' WHERE id = :integration_id"),
        {"integration_id": integration_id}
    )

    # Record sync history
    sync_result = await db.execute(
        text("""
            INSERT INTO org_sync_history (org_id, integration_id, sync_type, status)
            VALUES (:org_id, :integration_id, :sync_type, 'started')
            RETURNING id
        """),
        {"org_id": org_id, "integration_id": integration_id, "sync_type": sync_type}
    )
    sync_row = sync_result.fetchone()
    sync_id = str(sync_row.id) if sync_row else None

    await db.commit()

    # In production, this would be a background task
    # For now, simulate sync results
    try:
        records_processed = 0
        records_created = 0

        # Update sync status
        await db.execute(
            text("""
                UPDATE org_integrations SET sync_status = 'completed', last_sync_at = NOW(), sync_error = NULL
                WHERE id = :integration_id
            """),
            {"integration_id": integration_id}
        )

        # Update sync history
        if sync_id:
            await db.execute(
                text("""
                    UPDATE org_sync_history SET status = 'completed', completed_at = NOW(), records_processed = :processed, records_created = :created
                    WHERE id = :sync_id
                """),
                {"sync_id": sync_id, "processed": records_processed, "created": records_created}
            )

        await db.commit()

        return {
            "status": "completed",
            "sync_id": sync_id,
            "records_processed": records_processed,
            "records_created": records_created
        }

    except Exception as e:
        # Update with error
        await db.execute(
            text("UPDATE org_integrations SET sync_status = 'error', sync_error = :error WHERE id = :integration_id"),
            {"integration_id": integration_id, "error": str(e)}
        )

        if sync_id:
            await db.execute(
                text("UPDATE org_sync_history SET status = 'failed', completed_at = NOW() WHERE id = :sync_id"),
                {"sync_id": sync_id}
            )

        await db.commit()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/{integration_id}/sync-history")
async def get_sync_history(
    org_id: str,
    integration_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get sync history for an integration."""
    result = await db.execute(
        text("""
            SELECT * FROM org_sync_history
            WHERE integration_id = :integration_id
            ORDER BY started_at DESC
            LIMIT :limit
        """),
        {"integration_id": integration_id, "limit": limit}
    )

    history = []
    for row in result.fetchall():
        history.append({
            "id": str(row.id),
            "sync_type": row.sync_type,
            "status": row.status,
            "started_at": row.started_at,
            "completed_at": row.completed_at,
            "records_processed": row.records_processed,
            "records_created": row.records_created,
        })

    return {"history": history}


@router.patch("/{integration_id}")
async def update_integration(
    org_id: str,
    integration_id: str,
    update: IntegrationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update integration settings."""
    existing = await db.execute(
        text("SELECT id FROM org_integrations WHERE org_id = :org_id AND id = :integration_id"),
        {"org_id": org_id, "integration_id": integration_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="Integration not found")

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Build SET clause
    set_parts = []
    params = {"integration_id": integration_id}
    for key, value in update_data.items():
        set_parts.append(f"{key} = :{key}")
        params[key] = value

    set_clause = ", ".join(set_parts)

    result = await db.execute(
        text(f"""
            UPDATE org_integrations SET {set_clause}, updated_at = NOW()
            WHERE id = :integration_id
            RETURNING id, provider, status, config, metadata, created_at, updated_at
        """),
        params
    )
    await db.commit()

    row = result.fetchone()
    return {
        "id": str(row.id),
        "provider": row.provider,
        "status": row.status,
        "config": row.config,
        "metadata": row.metadata,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.delete("/{integration_id}")
async def disconnect_integration(
    org_id: str,
    integration_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Disconnect an integration."""
    existing = await db.execute(
        text("SELECT id FROM org_integrations WHERE org_id = :org_id AND id = :integration_id"),
        {"org_id": org_id, "integration_id": integration_id}
    )
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="Integration not found")

    # In production, would also revoke OAuth tokens

    await db.execute(
        text("DELETE FROM org_integrations WHERE id = :integration_id"),
        {"integration_id": integration_id}
    )
    await db.commit()

    return {"status": "disconnected", "integration_id": integration_id}


# =============================================================================
# SSO CONFIGURATION
# =============================================================================

@router.get("/sso/config")
async def get_sso_config(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get SSO configuration for organization."""
    result = await db.execute(
        text("SELECT sso_provider, sso_config FROM organizations WHERE id = :org_id"),
        {"org_id": org_id}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "sso_enabled": row.sso_provider is not None,
        "provider": row.sso_provider,
        "config": row.sso_config or {}
    }


@router.post("/sso/config")
async def configure_sso(
    org_id: str,
    provider: str,
    config: dict,
    db: AsyncSession = Depends(get_db)
):
    """Configure SSO for organization."""
    valid_providers = ["google", "microsoft", "okta", "saml"]
    if provider not in valid_providers:
        raise HTTPException(status_code=400, detail=f"Invalid SSO provider. Must be one of: {valid_providers}")

    # Validate required config fields based on provider
    required_fields = {
        "google": ["client_id", "client_secret"],
        "microsoft": ["client_id", "client_secret", "tenant_id"],
        "okta": ["domain", "client_id", "client_secret"],
        "saml": ["idp_entity_id", "idp_sso_url", "idp_certificate"]
    }

    missing = [f for f in required_fields.get(provider, []) if f not in config]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required config fields: {missing}")

    import json
    await db.execute(
        text("UPDATE organizations SET sso_provider = :provider, sso_config = :config WHERE id = :org_id"),
        {"org_id": org_id, "provider": provider, "config": json.dumps(config)}
    )
    await db.commit()

    return {"status": "configured", "provider": provider}


@router.delete("/sso/config")
async def disable_sso(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Disable SSO for organization."""
    await db.execute(
        text("UPDATE organizations SET sso_provider = NULL, sso_config = NULL WHERE id = :org_id"),
        {"org_id": org_id}
    )
    await db.commit()

    return {"status": "disabled"}
