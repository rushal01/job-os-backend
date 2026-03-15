"""Email intelligence service — Gmail scanning and status updates.

Scans inbox for job-related emails (rejections, interview invites, offers)
and auto-updates application statuses.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession


async def get_email_settings(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Get email integration settings for a user."""
    raise NotImplementedError


async def update_email_settings(db: AsyncSession, user_id: uuid.UUID, settings: dict) -> dict:
    """Update email integration settings."""
    raise NotImplementedError


async def trigger_email_scan(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Queue an async email scan task. Returns task_id."""
    raise NotImplementedError
