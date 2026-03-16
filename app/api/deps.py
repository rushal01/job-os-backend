
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.core.security import verify_jwt
from app.db.session import get_db
from app.models.user import User


async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and verify JWT from Authorization header, look up the user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(
            code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Missing or invalid Authorization header",
        )

    token = authorization.removeprefix("Bearer ").strip()
    payload = verify_jwt(token)
    supabase_uid = payload["sub"]

    result = await db.execute(
        select(User).where(User.supabase_uid == supabase_uid)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="User not found",
        )

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
