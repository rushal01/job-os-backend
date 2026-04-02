"""Admin service — user management, system health, feature flags.

Implements admin logic per API Contract Section 4.13.
Requires super_admin role for all operations.
"""

import base64
import json
import time
import uuid

from loguru import logger
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.db.redis import redis_client
from app.models.user import User, UserRole

# Track process start time for uptime
_start_time = time.time()

DEFAULT_FEATURE_FLAGS = {
    "ai_scoring": True,
    "email_scanning": False,
    "auto_apply": False,
    "market_intelligence": True,
    "copilot": True,
}


async def list_users(
    db: AsyncSession,
    cursor: str | None,
    limit: int,
    search: str | None,
) -> tuple[list[User], str | None, bool]:
    """List all users with cursor pagination and optional search."""
    query = select(User).order_by(User.created_at.desc())

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(search_term),
                User.full_name.ilike(search_term),
            )
        )

    # Decode cursor (base64-encoded offset)
    offset = 0
    if cursor:
        try:
            offset = int(base64.b64decode(cursor).decode())
        except (ValueError, Exception):
            logger.warning("Invalid cursor: {}", cursor)

    query = query.offset(offset).limit(limit + 1)

    result = await db.execute(query)
    users = list(result.scalars().all())

    has_more = len(users) > limit
    if has_more:
        users = users[:limit]

    next_cursor = None
    if has_more:
        next_offset = offset + limit
        next_cursor = base64.b64encode(str(next_offset).encode()).decode()

    return users, next_cursor, has_more


async def get_user_detail(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Get detailed user info including settings and supabase_uid."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user_role(
    db: AsyncSession, user_id: uuid.UUID, role: str
) -> User:
    """Update a user's role."""
    # Validate role is a valid UserRole
    try:
        valid_role = UserRole(role)
    except ValueError as e:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Invalid role: {role}. Must be one of: {[r.value for r in UserRole]}",
        ) from e

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="User not found")

    user.role = valid_role
    await db.flush()
    await db.refresh(user)

    logger.info("Updated user {} role to {}", user_id, role)
    return user


async def suspend_user(
    db: AsyncSession, user_id: uuid.UUID, reason: str
) -> User:
    """Suspend a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="User not found")

    current_settings = dict(user.settings) if user.settings else {}
    current_settings["suspended"] = True
    current_settings["suspend_reason"] = reason
    user.settings = current_settings
    await db.flush()
    await db.refresh(user)

    logger.info("Suspended user {} for reason: {}", user_id, reason)
    return user


async def get_system_health(db: AsyncSession) -> dict:
    """Get system health: database, redis, celery workers, queue depth."""
    health: dict = {
        "database": "unknown",
        "redis": "unknown",
        "celery_workers": 0,
        "queue_depth": 0,
        "uptime_seconds": round(time.time() - _start_time, 2),
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        health["database"] = "healthy"
    except Exception as exc:
        logger.error("Database health check failed: {}", exc)
        health["database"] = "unhealthy"

    # Check Redis
    if redis_client is not None:
        try:
            await redis_client.ping()
            health["redis"] = "healthy"
        except Exception as exc:
            logger.error("Redis health check failed: {}", exc)
            health["redis"] = "unhealthy"
    else:
        health["redis"] = "unavailable"

    # Check Celery workers
    try:
        from app.tasks.celery_app import celery_app

        inspect = celery_app.control.inspect()
        active_workers = inspect.ping()
        if active_workers:
            health["celery_workers"] = len(active_workers)

        # Queue depth
        reserved = inspect.reserved()
        if reserved:
            health["queue_depth"] = sum(
                len(tasks) for tasks in reserved.values()
            )
    except Exception as exc:
        logger.warning("Celery inspection failed: {}", exc)
        health["celery_workers"] = 0
        health["queue_depth"] = 0

    logger.info("System health check: {}", health)
    return health


async def get_feature_flags(db: AsyncSession) -> dict:
    """Get feature flag configuration."""
    if redis_client is not None:
        try:
            raw = await redis_client.get("feature_flags")
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("Failed to read feature flags from Redis: {}", exc)

    return dict(DEFAULT_FEATURE_FLAGS)


async def update_feature_flags(db: AsyncSession, flags: dict) -> dict:
    """Update feature flags."""
    if redis_client is not None:
        try:
            await redis_client.set("feature_flags", json.dumps(flags))
            logger.info("Updated feature flags: {}", flags)
            return flags
        except Exception as exc:
            logger.error("Failed to write feature flags to Redis: {}", exc)
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update feature flags",
            ) from exc
    else:
        raise AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Redis is unavailable, cannot update feature flags",
        )
