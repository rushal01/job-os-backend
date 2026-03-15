"""Auth service — proxies to Supabase Auth and manages local User records."""

import httpx
from loguru import logger
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
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def supabase_signup(email: str, password: str) -> dict:
    """Register a new user via Supabase Auth."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_SUPABASE_AUTH_URL}/signup",
                json={"email": email, "password": password},
                headers=_HEADERS,
            )
    except httpx.TimeoutException:
        logger.error("Supabase Auth signup request timed out")
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Authentication service is temporarily unavailable. Please try again.",
        ) from None
    except httpx.ConnectError:
        logger.error("Cannot connect to Supabase Auth for signup")
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Authentication service is unreachable. Please try again later.",
        ) from None
    if resp.status_code >= 400:
        data = resp.json()
        msg = data.get("msg") or data.get("error_description") or "Signup failed"
        raise AppError(code=ErrorCode.RESOURCE_ALREADY_EXISTS, message=msg)
    return resp.json()


async def supabase_login(email: str, password: str) -> dict:
    """Authenticate via Supabase Auth (email/password)."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_SUPABASE_AUTH_URL}/token?grant_type=password",
                json={"email": email, "password": password},
                headers=_HEADERS,
            )
    except httpx.TimeoutException:
        logger.error("Supabase Auth login request timed out")
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Authentication service is temporarily unavailable. Please try again.",
        ) from None
    except httpx.ConnectError:
        logger.error("Cannot connect to Supabase Auth for login")
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Authentication service is unreachable. Please try again later.",
        ) from None
    if resp.status_code >= 400:
        raise AppError(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Invalid email or password",
        )
    return resp.json()


async def supabase_refresh(refresh_token: str) -> dict:
    """Refresh a session via Supabase Auth."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_SUPABASE_AUTH_URL}/token?grant_type=refresh_token",
                json={"refresh_token": refresh_token},
                headers=_HEADERS,
            )
    except httpx.TimeoutException:
        logger.error("Supabase Auth refresh request timed out")
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Authentication service is temporarily unavailable. Please try again.",
        ) from None
    except httpx.ConnectError:
        logger.error("Cannot connect to Supabase Auth for refresh")
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Authentication service is unreachable. Please try again later.",
        ) from None
    if resp.status_code >= 400:
        raise AppError(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Token refresh failed",
        )
    data = resp.json()
    return {"session": {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data.get("expires_in", 3600),
        "token_type": data.get("token_type", "bearer"),
    }}


async def supabase_logout(access_token: str) -> None:
    """Revoke a session via Supabase Auth."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_SUPABASE_AUTH_URL}/logout",
                headers={**_HEADERS, "Authorization": f"Bearer {access_token}"},
            )
    except httpx.TimeoutException:
        logger.error("Supabase Auth logout request timed out")
        raise AppError(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Session revocation timed out",
        ) from None
    except httpx.ConnectError:
        logger.error("Cannot connect to Supabase Auth for logout")
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Authentication service is unreachable. Please try again later.",
        ) from None
    if resp.status_code >= 400:
        raise AppError(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Session revocation failed",
        )


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
