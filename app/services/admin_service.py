"""Admin service — user management, system health, feature flags.

Implements admin logic per API Contract Section 4.13.
Requires super_admin role for all operations.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def list_users(db: AsyncSession, cursor: str | None, limit: int, search: str | None) -> tuple[list[User], str | None, bool]:
    """List all users with cursor pagination and optional search."""
    raise NotImplementedError


async def get_user_detail(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Get detailed user info including settings and supabase_uid."""
    raise NotImplementedError


async def update_user_role(db: AsyncSession, user_id: uuid.UUID, role: str) -> User:
    """Update a user's role."""
    raise NotImplementedError


async def suspend_user(db: AsyncSession, user_id: uuid.UUID, reason: str) -> User:
    """Suspend a user account."""
    raise NotImplementedError


async def get_system_health(db: AsyncSession) -> dict:
    """Get system health: database, redis, celery workers, queue depth."""
    raise NotImplementedError


async def get_feature_flags(db: AsyncSession) -> dict:
    """Get feature flag configuration."""
    raise NotImplementedError


async def update_feature_flags(db: AsyncSession, flags: dict) -> dict:
    """Update feature flags."""
    raise NotImplementedError
