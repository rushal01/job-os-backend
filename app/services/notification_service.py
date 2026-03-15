"""Notification service — create, list, mark read, count unread.

Implements notification logic per API Contract Section 4.10.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def list_notifications(
    db: AsyncSession, user_id: uuid.UUID, cursor: str | None, limit: int,
    priority: str | None, unread_only: bool,
) -> tuple[list[Notification], str | None, bool]:
    """List notifications with cursor pagination."""
    raise NotImplementedError


async def mark_read(db: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    """Mark a single notification as read."""
    raise NotImplementedError


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Mark all notifications as read. Returns count of updated notifications."""
    raise NotImplementedError


async def get_unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Get count of unread notifications."""
    raise NotImplementedError


async def create_notification(
    db: AsyncSession, user_id: uuid.UUID, type: str, title: str,
    body: str | None = None, priority: str = "medium",
    action_url: str | None = None, extra_data: dict | None = None,
) -> Notification:
    """Create a new notification (called by services, not directly by API)."""
    raise NotImplementedError
