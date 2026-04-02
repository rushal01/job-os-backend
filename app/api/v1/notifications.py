"""Notifications API endpoints — API Contract Section 4.10.

4 endpoints: list, mark read, mark all read, unread count.
"""

import base64
import contextlib
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import DataResponse, PaginatedResponse
from app.schemas.notification import (
    NotificationResponse,
    ReadAllResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/notifications")


@router.get("", response_model=PaginatedResponse[NotificationResponse])
async def list_notifications(
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    priority: str | None = None,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[NotificationResponse]:
    """List notifications with cursor pagination."""
    query = select(Notification).where(
        Notification.user_id == current_user.id,
    ).order_by(Notification.created_at.desc())

    if unread_only:
        query = query.where(Notification.read == False)  # noqa: E712

    if priority:
        query = query.where(Notification.priority == priority)

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

    return {"data": items, "next_cursor": next_cursor, "has_more": has_more}


@router.put("/{notification_id}/read", response_model=DataResponse[NotificationResponse])
async def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[NotificationResponse]:
    """Mark a notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Notification not found")

    notification.read = True
    await db.commit()
    await db.refresh(notification)
    return {"data": notification}


@router.put("/read-all", response_model=ReadAllResponse)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReadAllResponse:
    """Mark all notifications as read."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.read == False,  # noqa: E712
        )
        .values(read=True)
    )
    await db.commit()
    return {"updated": result.rowcount}


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    """Get count of unread notifications."""
    count = (await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.read == False,  # noqa: E712
        )
    )).scalar() or 0

    return {"count": count}
