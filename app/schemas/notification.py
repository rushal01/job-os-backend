"""Notification schemas — API Contract Section 4.10.

Defines response models for notification listing and management.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Full notification returned by API."""

    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    priority: str
    title: str
    body: str | None = None
    read: bool
    action_url: str | None = None
    extra_data: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    """Response from GET /notifications/unread-count."""

    count: int


class ReadAllResponse(BaseModel):
    """Response from PUT /notifications/read-all."""

    updated: int
