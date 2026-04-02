"""Email intelligence service — Gmail scanning and status updates.

Scans inbox for job-related emails (rejections, interview invites, offers)
and auto-updates application statuses.
"""

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.models.task import Task
from app.models.user import User

DEFAULT_EMAIL_SETTINGS = {
    "gmail_connected": False,
    "auto_scan": False,
    "scan_frequency_minutes": 30,
}


async def get_email_settings(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Get email integration settings for a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="User not found")

    settings = user.settings or {}
    return settings.get("email_settings", dict(DEFAULT_EMAIL_SETTINGS))


async def update_email_settings(db: AsyncSession, user_id: uuid.UUID, settings: dict) -> dict:
    """Update email integration settings."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="User not found")

    current_settings = dict(user.settings) if user.settings else {}
    current_settings["email_settings"] = settings
    user.settings = current_settings
    await db.flush()
    await db.refresh(user)

    logger.info("Updated email settings for user {}", user_id)
    return user.settings["email_settings"]


async def trigger_email_scan(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Queue an async email scan task. Returns task_id."""
    from app.tasks.email_tasks import scan_inbox

    task = Task(
        user_id=user_id,
        task_name="email_scan",
        status="pending",
        progress_pct=0.0,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    celery_result = scan_inbox.delay(str(user_id))
    task.celery_task_id = celery_result.id
    await db.commit()

    logger.info("Triggered email scan for user {}, task_id={}", user_id, task.id)
    return str(task.id)
