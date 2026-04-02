
from fastapi import Depends, Header
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.core.security import verify_jwt
from app.db.session import get_db
from app.models.user import User, UserRole


async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and verify JWT from Authorization header, look up the user.

    If the JWT is valid but no local User record exists (e.g. the user signed
    up via the Supabase client SDK and verified their email), a local record is
    created automatically (just-in-time provisioning).
    """
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning(
            "get_current_user: no valid Authorization header (got: {})",
            repr(authorization)[:80] if authorization else "None",
        )
        raise AppError(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Missing or invalid Authorization header",
        )

    token = authorization.removeprefix("Bearer ").strip()
    logger.debug("get_current_user: token length={} first20={}...", len(token), token[:20])
    payload = verify_jwt(token)
    supabase_uid = payload["sub"]

    result = await db.execute(
        select(User).where(User.supabase_uid == supabase_uid)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Just-in-time provisioning: create a local record from JWT claims
        email = payload.get("email")
        if not email:
            raise AppError(
                code=ErrorCode.AUTH_INVALID_TOKEN,
                message="Token missing email claim",
            )
        user_metadata = payload.get("user_metadata", {})
        full_name = user_metadata.get("full_name")

        logger.info(
            "Auto-provisioning local user for supabase_uid={} email={}",
            supabase_uid,
            email,
        )
        user = User(
            email=email,
            supabase_uid=supabase_uid,
            full_name=full_name,
            role=UserRole.USER,
            settings={},
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require super_admin role."""
    from app.models.user import UserRole

    if current_user.role != UserRole.SUPER_ADMIN:
        raise AppError(
            code=ErrorCode.AUTH_INSUFFICIENT_ROLE,
            message="Insufficient permissions — super_admin role required",
        )
    return current_user
