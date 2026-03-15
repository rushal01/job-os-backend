"""Auth service — proxies to Supabase Auth and manages local User records."""

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Supabase Auth REST helpers
# ---------------------------------------------------------------------------

_SUPABASE_AUTH_URL = f"{settings.SUPABASE_URL}/auth/v1"
_HEADERS = {
    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    "Content-Type": "application/json",
}


async def supabase_signup(email: str, password: str) -> dict:
    """Register a new user via Supabase Auth."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_SUPABASE_AUTH_URL}/signup",
            json={"email": email, "password": password},
            headers=_HEADERS,
        )
    if resp.status_code >= 400:
        data = resp.json()
        msg = data.get("msg") or data.get("error_description") or "Signup failed"
        raise Exception(msg)
    return resp.json()


async def supabase_login(email: str, password: str) -> dict:
    """Authenticate via Supabase Auth (email/password)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_SUPABASE_AUTH_URL}/token?grant_type=password",
            json={"email": email, "password": password},
            headers=_HEADERS,
        )
    if resp.status_code >= 400:
        raise Exception("Invalid login credentials")
    return resp.json()


async def supabase_refresh(refresh_token: str) -> dict:
    """Refresh a session via Supabase Auth."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_SUPABASE_AUTH_URL}/token?grant_type=refresh_token",
            json={"refresh_token": refresh_token},
            headers=_HEADERS,
        )
    if resp.status_code >= 400:
        raise Exception("Token refresh failed")
    data = resp.json()
    return {"session": {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data.get("expires_in", 3600),
        "token_type": data.get("token_type", "bearer"),
    }}


async def supabase_logout(access_token: str) -> None:
    """Revoke a session via Supabase Auth."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_SUPABASE_AUTH_URL}/logout",
            headers={**_HEADERS, "Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code >= 400:
        raise Exception("Logout failed")


# ---------------------------------------------------------------------------
# Local user management
# ---------------------------------------------------------------------------

async def create_user(
    db: AsyncSession,
    email: str,
    supabase_uid: str,
    full_name: str | None = None,
) -> User:
    """Create a local User record after Supabase signup."""
    user = User(
        email=email,
        supabase_uid=supabase_uid,
        full_name=full_name,
        role=UserRole.USER,
        settings={},
    )
    db.add(user)
    await db.flush()
    return user


async def get_user_by_supabase_uid(
    db: AsyncSession, supabase_uid: str
) -> User | None:
    """Look up a local user by their Supabase UID."""
    result = await db.execute(
        select(User).where(User.supabase_uid == supabase_uid)
    )
    return result.scalar_one_or_none()
