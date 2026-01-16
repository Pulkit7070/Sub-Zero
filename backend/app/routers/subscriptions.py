"""Subscription management endpoints."""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.schemas import (
    SubscriptionResponse,
    SubscriptionCreate,
    SubscriptionUpdate,
    SyncRequest,
    SyncResponse,
)
from app.routers.auth import verify_token
from app.services.gmail import GmailService, refresh_gmail_token, TokenRefreshError
from app.services.parser import EmailParser, deduplicate_subscriptions
from app.utils.encryption import decrypt_token

# Sync lock timeout - if a sync is running for longer than this, allow override
SYNC_LOCK_TIMEOUT_MINUTES = 10

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


@router.get("", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    status_filter: Optional[str] = None,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all subscriptions for the current user."""
    query = """
        SELECT id, vendor_name, vendor_normalized, amount_cents, currency,
               billing_cycle, last_charge_at, next_renewal_at, status,
               source, confidence, created_at, updated_at
        FROM subscriptions
        WHERE user_id = :user_id
    """

    params = {"user_id": str(user_id)}

    if status_filter:
        query += " AND status = :status"
        params["status"] = status_filter

    query += " ORDER BY updated_at DESC"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return [
        SubscriptionResponse(
            id=row[0],
            vendor_name=row[1],
            vendor_normalized=row[2],
            amount_cents=row[3],
            currency=row[4],
            billing_cycle=row[5],
            last_charge_at=row[6],
            next_renewal_at=row[7],
            status=row[8],
            source=row[9],
            confidence=row[10],
            created_at=row[11],
            updated_at=row[12],
        )
        for row in rows
    ]


async def acquire_sync_lock(
    db: AsyncSession,
    data_source_id: UUID,
) -> bool:
    """
    Attempt to acquire a sync lock.

    Returns True if lock acquired, False if already locked.
    Stale locks (>10 min) are automatically overridden.
    """
    now = datetime.now(timezone.utc)
    lock_timeout = now - timedelta(minutes=SYNC_LOCK_TIMEOUT_MINUTES)

    # Try to acquire lock (only if not locked or lock is stale)
    result = await db.execute(
        text("""
        UPDATE data_sources
        SET sync_in_progress = TRUE, sync_started_at = :now
        WHERE id = :id
          AND (sync_in_progress = FALSE
               OR sync_started_at IS NULL
               OR sync_started_at < :lock_timeout)
        RETURNING id
        """),
        {"id": str(data_source_id), "now": now, "lock_timeout": lock_timeout},
    )
    row = result.fetchone()
    await db.commit()
    return row is not None


async def release_sync_lock(db: AsyncSession, data_source_id: UUID) -> None:
    """Release the sync lock."""
    await db.execute(
        text("""
        UPDATE data_sources
        SET sync_in_progress = FALSE, sync_started_at = NULL
        WHERE id = :id
        """),
        {"id": str(data_source_id)},
    )
    await db.commit()


async def get_processed_message_ids(db: AsyncSession, user_id: UUID) -> set[str]:
    """Get set of already processed message IDs for a user."""
    result = await db.execute(
        text("SELECT message_id FROM processed_emails WHERE user_id = :user_id"),
        {"user_id": str(user_id)},
    )
    return {row[0] for row in result.fetchall()}


async def mark_messages_as_processed(
    db: AsyncSession,
    user_id: UUID,
    message_ids: list[str],
) -> None:
    """Mark message IDs as processed."""
    if not message_ids:
        return

    # Use batch insert with ON CONFLICT to handle duplicates
    for message_id in message_ids:
        await db.execute(
            text("""
            INSERT INTO processed_emails (user_id, message_id)
            VALUES (:user_id, :message_id)
            ON CONFLICT (user_id, message_id) DO NOTHING
            """),
            {"user_id": str(user_id), "message_id": message_id},
        )


@router.post("/sync", response_model=SyncResponse)
async def sync_subscriptions(
    request: SyncRequest = SyncRequest(),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Sync subscriptions from Gmail."""
    print(f"[SYNC] Starting sync for user {user_id}, force={request.force}, days_back={request.days_back}")

    # Get user's Gmail data source
    result = await db.execute(
        text("""
        SELECT id, access_token_encrypted, refresh_token_encrypted,
               token_expires_at, last_sync_at, sync_in_progress, sync_started_at
        FROM data_sources
        WHERE user_id = :user_id AND provider = 'gmail' AND status = 'active'
        """),
        {"user_id": str(user_id)},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Gmail connection found. Please connect your Gmail account.",
        )

    data_source_id = row[0]
    access_token_encrypted = row[1]
    refresh_token_encrypted = row[2]
    token_expires_at = row[3]
    last_sync_at = row[4]
    sync_in_progress = row[5]
    sync_started_at = row[6]

    # Check for existing sync lock
    print(f"[SYNC] Attempting to acquire lock for data_source {data_source_id}")
    if not await acquire_sync_lock(db, data_source_id):
        print("[SYNC] Lock acquisition failed - sync already in progress")
        return SyncResponse(
            status="locked",
            subscriptions_found=0,
            new_subscriptions=0,
            updated_subscriptions=0,
            emails_processed=0,
            emails_skipped=0,
            is_incremental=False,
            message="A sync is already in progress. Please wait and try again.",
        )
    print("[SYNC] Lock acquired successfully")

    try:
        # Check if token needs refresh
        if token_expires_at and token_expires_at < datetime.now(timezone.utc):
            if not refresh_token_encrypted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Gmail token expired. Please reconnect your account.",
                )

            # Refresh the token with retry logic
            try:
                new_access, new_refresh, new_expires = await refresh_gmail_token(
                    refresh_token_encrypted
                )

                await db.execute(
                    text("""
                    UPDATE data_sources
                    SET access_token_encrypted = :access_token,
                        refresh_token_encrypted = :refresh_token,
                        token_expires_at = :expires_at
                    WHERE id = :id
                    """),
                    {
                        "id": str(data_source_id),
                        "access_token": new_access,
                        "refresh_token": new_refresh,
                        "expires_at": new_expires,
                    },
                )
                await db.commit()

                access_token_encrypted = new_access
            except TokenRefreshError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(e),
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to refresh Gmail token. Please reconnect your account.",
                )

        # Decrypt access token
        access_token = decrypt_token(access_token_encrypted)

        # Determine sync mode (incremental vs full)
        is_incremental = False
        sync_from_date: Optional[datetime] = None

        if last_sync_at and not request.force:
            # Use incremental sync from last sync date
            is_incremental = True
            sync_from_date = last_sync_at
        else:
            # Full sync using days_back
            sync_from_date = datetime.now(timezone.utc) - timedelta(days=request.days_back)

        # Initialize Gmail service and parser
        gmail_service = GmailService(access_token)
        parser = EmailParser()

        # Get already processed message IDs
        processed_ids = await get_processed_message_ids(db, user_id)

        # Fetch emails
        try:
            print(f"[SYNC] Fetching emails - incremental: {is_incremental}, from_date: {sync_from_date}")
            emails = await gmail_service.fetch_receipt_emails(
                after_date=sync_from_date if is_incremental else None,
                days_back=request.days_back,
            )
            print(f"[SYNC] Fetched {len(emails)} emails from Gmail")
        except Exception as e:
            import traceback
            print(f"[SYNC] Error fetching emails: {e}")
            print(f"[SYNC] Full traceback:\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch emails: {str(e)}",
            )

        # Filter out already processed emails
        emails_skipped = 0
        new_emails = []
        for email_data in emails:
            if email_data.get("message_id") in processed_ids:
                emails_skipped += 1
            else:
                new_emails.append(email_data)

        # Parse emails into subscriptions
        parsed_subs = []
        newly_processed_ids = []
        parse_count = 0
        for email_data in new_emails:
            parsed = parser.parse_email(email_data)
            if parsed:
                parse_count += 1
                print(f"[SYNC] Parsed: {parsed.vendor_name} - confidence: {parsed.confidence:.2f}")
                if parsed.confidence >= 0.3:  # Lower threshold
                    parsed_subs.append(parsed)
            # Track message as processed regardless of parse result
            if email_data.get("message_id"):
                newly_processed_ids.append(email_data["message_id"])

        print(f"[SYNC] Parsed {parse_count} emails, {len(parsed_subs)} passed threshold (from {len(new_emails)} total)")

        # Deduplicate
        unique_subs = deduplicate_subscriptions(parsed_subs)

        # Get existing subscriptions
        existing_result = await db.execute(
            text("""
            SELECT id, vendor_normalized
            FROM subscriptions
            WHERE user_id = :user_id
            """),
            {"user_id": str(user_id)},
        )
        existing_rows = existing_result.fetchall()
        existing_vendors = {row[1]: row[0] for row in existing_rows}

        new_count = 0
        updated_count = 0

        for sub in unique_subs:
            if sub.vendor_normalized in existing_vendors:
                # Update existing subscription
                await db.execute(
                    text("""
                    UPDATE subscriptions
                    SET amount_cents = COALESCE(:amount_cents, amount_cents),
                        currency = :currency,
                        billing_cycle = COALESCE(:billing_cycle, billing_cycle),
                        last_charge_at = GREATEST(last_charge_at, :charge_date),
                        confidence = GREATEST(confidence, :confidence),
                        raw_data = :raw_data,
                        updated_at = NOW()
                    WHERE id = :id
                    """),
                    {
                        "id": str(existing_vendors[sub.vendor_normalized]),
                        "amount_cents": sub.amount_cents,
                        "currency": sub.currency,
                        "billing_cycle": sub.billing_cycle,
                        "charge_date": sub.charge_date,
                        "confidence": sub.confidence,
                        "raw_data": json.dumps(sub.raw_data) if sub.raw_data else None,
                    },
                )
                updated_count += 1
            else:
                # Insert new subscription
                await db.execute(
                    text("""
                    INSERT INTO subscriptions (
                        user_id, vendor_name, vendor_normalized, amount_cents,
                        currency, billing_cycle, last_charge_at, source,
                        confidence, raw_data
                    ) VALUES (
                        :user_id, :vendor_name, :vendor_normalized, :amount_cents,
                        :currency, :billing_cycle, :charge_date, 'gmail',
                        :confidence, :raw_data
                    )
                    """),
                    {
                        "user_id": str(user_id),
                        "vendor_name": sub.vendor_name,
                        "vendor_normalized": sub.vendor_normalized,
                        "amount_cents": sub.amount_cents,
                        "currency": sub.currency,
                        "billing_cycle": sub.billing_cycle,
                        "charge_date": sub.charge_date,
                        "confidence": sub.confidence,
                        "raw_data": json.dumps(sub.raw_data) if sub.raw_data else None,
                    },
                )
                new_count += 1

        # Mark newly processed emails
        await mark_messages_as_processed(db, user_id, newly_processed_ids)

        # Update last sync timestamp and release lock
        await db.execute(
            text("""
            UPDATE data_sources
            SET last_sync_at = NOW(),
                sync_in_progress = FALSE,
                sync_started_at = NULL
            WHERE id = :id
            """),
            {"id": str(data_source_id)},
        )

        await db.commit()

        await db.commit()
        print(f"[SYNC] ✓ Completed: {new_count} new, {updated_count} updated subscriptions")

        return SyncResponse(
            status="completed",
            subscriptions_found=len(unique_subs),
            new_subscriptions=new_count,
            updated_subscriptions=updated_count,
            emails_processed=len(new_emails),
            emails_skipped=emails_skipped,
            is_incremental=is_incremental,
            sync_from_date=sync_from_date,
            message=f"Detected {len(unique_subs)} likely subscriptions (source: gmail_inference)",
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        await db.rollback()
        raise
    except Exception as e:
        # PHASE 7: Proper rollback on error
        await db.rollback()
        import traceback
        print(f"[SYNC] Error: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )
    finally:
        # PHASE 7: Always release lock in finally block
        await release_sync_lock(db, data_source_id)


@router.post("", response_model=SubscriptionResponse)
async def create_subscription(
    subscription: SubscriptionCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a subscription."""
    # Normalize vendor name
    vendor_normalized = subscription.vendor_normalized or subscription.vendor_name.lower().replace(" ", "")

    result = await db.execute(
        """
        INSERT INTO subscriptions (
            user_id, vendor_name, vendor_normalized, amount_cents,
            currency, billing_cycle, last_charge_at, next_renewal_at,
            source, confidence, raw_data
        ) VALUES (
            :user_id, :vendor_name, :vendor_normalized, :amount_cents,
            :currency, :billing_cycle, :last_charge_at, :next_renewal_at,
            'manual', :confidence, :raw_data
        )
        RETURNING id, vendor_name, vendor_normalized, amount_cents, currency,
                  billing_cycle, last_charge_at, next_renewal_at, status,
                  source, confidence, created_at, updated_at
        """,
        {
            "user_id": str(user_id),
            "vendor_name": subscription.vendor_name,
            "vendor_normalized": vendor_normalized,
            "amount_cents": subscription.amount_cents,
            "currency": subscription.currency,
            "billing_cycle": subscription.billing_cycle.value if subscription.billing_cycle else None,
            "last_charge_at": subscription.last_charge_at,
            "next_renewal_at": subscription.next_renewal_at,
            "confidence": subscription.confidence,
            "raw_data": str(subscription.raw_data) if subscription.raw_data else None,
        },
    )

    row = result.fetchone()
    await db.commit()

    return SubscriptionResponse(
        id=row[0],
        vendor_name=row[1],
        vendor_normalized=row[2],
        amount_cents=row[3],
        currency=row[4],
        billing_cycle=row[5],
        last_charge_at=row[6],
        next_renewal_at=row[7],
        status=row[8],
        source=row[9],
        confidence=row[10],
        created_at=row[11],
        updated_at=row[12],
    )


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific subscription."""
    result = await db.execute(
        """
        SELECT id, vendor_name, vendor_normalized, amount_cents, currency,
               billing_cycle, last_charge_at, next_renewal_at, status,
               source, confidence, created_at, updated_at
        FROM subscriptions
        WHERE id = :id AND user_id = :user_id
        """,
        {"id": str(subscription_id), "user_id": str(user_id)},
    )

    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    return SubscriptionResponse(
        id=row[0],
        vendor_name=row[1],
        vendor_normalized=row[2],
        amount_cents=row[3],
        currency=row[4],
        billing_cycle=row[5],
        last_charge_at=row[6],
        next_renewal_at=row[7],
        status=row[8],
        source=row[9],
        confidence=row[10],
        created_at=row[11],
        updated_at=row[12],
    )


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: UUID,
    update: SubscriptionUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a subscription."""
    # Build dynamic update query
    update_fields = []
    params = {"id": str(subscription_id), "user_id": str(user_id)}

    if update.vendor_name is not None:
        update_fields.append("vendor_name = :vendor_name")
        params["vendor_name"] = update.vendor_name

    if update.amount_cents is not None:
        update_fields.append("amount_cents = :amount_cents")
        params["amount_cents"] = update.amount_cents

    if update.currency is not None:
        update_fields.append("currency = :currency")
        params["currency"] = update.currency

    if update.billing_cycle is not None:
        update_fields.append("billing_cycle = :billing_cycle")
        params["billing_cycle"] = update.billing_cycle.value

    if update.status is not None:
        update_fields.append("status = :status")
        params["status"] = update.status.value

    if update.next_renewal_at is not None:
        update_fields.append("next_renewal_at = :next_renewal_at")
        params["next_renewal_at"] = update.next_renewal_at

    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    update_fields.append("updated_at = NOW()")

    query = f"""
        UPDATE subscriptions
        SET {', '.join(update_fields)}
        WHERE id = :id AND user_id = :user_id
        RETURNING id, vendor_name, vendor_normalized, amount_cents, currency,
                  billing_cycle, last_charge_at, next_renewal_at, status,
                  source, confidence, created_at, updated_at
    """

    result = await db.execute(query, params)
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    await db.commit()

    return SubscriptionResponse(
        id=row[0],
        vendor_name=row[1],
        vendor_normalized=row[2],
        amount_cents=row[3],
        currency=row[4],
        billing_cycle=row[5],
        last_charge_at=row[6],
        next_renewal_at=row[7],
        status=row[8],
        source=row[9],
        confidence=row[10],
        created_at=row[11],
        updated_at=row[12],
    )


@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a subscription."""
    result = await db.execute(
        """
        DELETE FROM subscriptions
        WHERE id = :id AND user_id = :user_id
        RETURNING id
        """,
        {"id": str(subscription_id), "user_id": str(user_id)},
    )

    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    await db.commit()

    return {"message": "Subscription deleted successfully"}
