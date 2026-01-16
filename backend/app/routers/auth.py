"""Authentication router with Google OAuth."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.schemas import Token, UserResponse
from app.utils.encryption import encrypt_token, decrypt_token

router = APIRouter()
settings = get_settings()

# In-memory state storage (use Redis in production)
oauth_states: dict[str, datetime] = {}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    access_token: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current authenticated user from cookie."""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = verify_token(access_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Fetch user from database
    result = await db.execute(
        select("*").select_from(
            db.get_bind().dialect.identifier_preparer.quote("users")
        ).where("id" == user_id)
    )

    return {"user_id": UUID(user_id), "email": payload.get("email")}


@router.get("/google/login")
async def google_login():
    """Redirect to Google OAuth consent screen."""
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = datetime.now(timezone.utc)

    # Clean up old states (older than 10 minutes)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    oauth_states_to_remove = [s for s, t in oauth_states.items() if t < cutoff]
    for s in oauth_states_to_remove:
        del oauth_states[s]

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.backend_url}/auth/google/callback",
        "response_type": "code",
        "scope": " ".join(settings.gmail_scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }

    auth_url = f"{settings.google_auth_url}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback."""
    # Verify state
    if state not in oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )
    del oauth_states[state]

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            settings.google_token_url,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{settings.backend_url}/auth/google/callback",
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for tokens",
            )

        tokens = token_response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)

        # Get user info
        userinfo_response = await client.get(
            settings.google_userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info",
            )

        userinfo = userinfo_response.json()
        email = userinfo.get("email")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Google",
        )

    # Check if user exists or create new one
    from sqlalchemy import text
    user_result = await db.execute(
        text("SELECT id, email, created_at FROM users WHERE email = :email"),
        {"email": email},
    )
    user_row = user_result.fetchone()

    if user_row:
        user_id = user_row[0]
    else:
        # Create new user
        insert_result = await db.execute(
            text("INSERT INTO users (email) VALUES (:email) RETURNING id"),
            {"email": email},
        )
        user_id = insert_result.fetchone()[0]
        await db.commit()

    # Calculate token expiry
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Encrypt tokens
    encrypted_access = encrypt_token(access_token)
    encrypted_refresh = encrypt_token(refresh_token) if refresh_token else None

    # Upsert data source
    await db.execute(
        text("""
        INSERT INTO data_sources (user_id, provider, access_token_encrypted, refresh_token_encrypted, token_expires_at, status)
        VALUES (:user_id, 'gmail', :access_token, :refresh_token, :expires_at, 'active')
        ON CONFLICT (user_id, provider) DO UPDATE SET
            access_token_encrypted = :access_token,
            refresh_token_encrypted = COALESCE(:refresh_token, data_sources.refresh_token_encrypted),
            token_expires_at = :expires_at,
            status = 'active'
        """),
        {
            "user_id": str(user_id),
            "access_token": encrypted_access,
            "refresh_token": encrypted_refresh,
            "expires_at": token_expires_at,
        },
    )
    await db.commit()

    # Create our JWT token
    jwt_token = create_access_token(
        data={"sub": str(user_id), "email": email}
    )

    # Redirect to frontend with token in cookie
    response = RedirectResponse(url=f"{settings.frontend_url}/dashboard")
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )

    return response


@router.post("/logout")
async def logout(response: Response):
    """Clear authentication cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    access_token: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user."""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = verify_token(access_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    email = payload.get("email")

    # Fetch user from database
    from sqlalchemy import text as sql_text
    result = await db.execute(
        sql_text("SELECT id, email, created_at FROM users WHERE id = :user_id"),
        {"user_id": user_id},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(id=row[0], email=row[1], created_at=row[2])
