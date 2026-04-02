"""Notification service — create, list, mark read, count unread.

Implements notification logic per API Contract Section 4.10.
"""

import base64
import contextlib
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def list_notifications(
    db: AsyncSession, user_id: uuid.UUID, cursor: str | None, limit: int,
    priority: str | None, unread_only: bool,
) -> tuple[list[Notification], str | None, bool]:
    """List notifications with cursor pagination."""
    query = select(Notification).where(Notification.user_id == user_id)

    if unread_only:
        query = query.where(Notification.read == False)  # noqa: E712
    if priority:
        query = query.where(Notification.priority == priority)

    query = query.order_by(Notification.created_at.desc())

    # Cursor pagination using offset (base64-encoded integer)
    if cursor:
        with contextlib.suppress(ValueError, Exception):
            cursor_offset = int(base64.b64decode(cursor).decode())
            query = query.offset(cursor_offset)

    # Fetch limit+1 to determine has_more
    query = query.limit(limit + 1)
    result = await db.execute(query)
    items = list(result.scalars().all())

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = None
    if has_more:
        current_offset = 0
        if cursor:
            with contextlib.suppress(ValueError, Exception):
                current_offset = int(base64.b64decode(cursor).decode())
        next_offset = current_offset + limit
        next_cursor = base64.b64encode(str(next_offset).encode()).decode()

    return items, next_cursor, has_more


async def mark_read(db: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.read = True
    await db.commit()
    await db.refresh(notification)
    return notification


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Mark all notifications as read. Returns count of updated notifications."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.read == False,  # noqa: E712
        )
        .values(read=True)
    )
    await db.commit()
    return result.rowcount


async def get_unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Get count of unread notifications."""
    result = await db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.read == False,  # noqa: E712
        )
    )
    return result.scalar_one()


async def create_notification(
    db: AsyncSession, user_id: uuid.UUID, notification_type: str, title: str,
    body: str | None = None, priority: str = "medium",
    action_url: str | None = None, extra_data: dict | None = None,
) -> Notification:
    """Create a new notification (called by services, not directly by API)."""
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        body=body,
        priority=priority,
        action_url=action_url,
        extra_data=extra_data,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification
