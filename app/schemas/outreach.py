"""Outreach schemas — contacts and messages for recruiter/referral outreach.

Referenced by file tree spec: app/schemas/outreach.py
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OutreachContactCreate(BaseModel):
    """Create a new outreach contact."""

    job_id: uuid.UUID | None = None
    name: str = Field(..., max_length=255)
    title: str | None = None
    company: str | None = None
    linkedin_url: str | None = None
    email: str | None = None
    channel: str = "linkedin_dm"
    warmth: str = "cold"


class OutreachContactUpdate(BaseModel):
    """Update an outreach contact."""

    name: str | None = None
    title: str | None = None
    company: str | None = None
    linkedin_url: str | None = None
    email: str | None = None
    channel: str | None = None
    warmth: str | None = None
    status: str | None = None


class OutreachContactResponse(BaseModel):
    """Full outreach contact returned by API."""

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID | None = None
    name: str
    title: str | None = None
    company: str | None = None
    channel: str
    warmth: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OutreachMessageCreate(BaseModel):
    """Create a new outreach message."""

    contact_id: uuid.UUID
    content: str
    channel: str
    is_follow_up: bool = False
    follow_up_number: int | None = None


class OutreachMessageResponse(BaseModel):
    """Full outreach message returned by API."""

    id: uuid.UUID
    contact_id: uuid.UUID
    content: str
    channel: str
    status: str
    sent_at: datetime | None = None
    opened_at: datetime | None = None
    replied_at: datetime | None = None
    is_follow_up: bool
    follow_up_number: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
