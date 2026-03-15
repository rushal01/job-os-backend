"""Notifications API endpoints — API Contract Section 4.10.

4 endpoints: list, mark read, mark all read, unread count.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
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
    raise NotImplementedError


@router.put("/{notification_id}/read", response_model=DataResponse[NotificationResponse])
async def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[NotificationResponse]:
    """Mark a notification as read."""
    raise NotImplementedError


@router.put("/read-all", response_model=ReadAllResponse)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReadAllResponse:
    """Mark all notifications as read."""
    raise NotImplementedError


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    """Get count of unread notifications."""
    raise NotImplementedError
