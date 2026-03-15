"""Work experience schemas — CRUD request/response models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WorkExperienceCreate(BaseModel):
    """Create a work experience entry."""

    company: str = Field(..., max_length=255)
    title: str = Field(..., max_length=255)
    start_date: str = Field(..., max_length=20)
    end_date: str | None = None
    is_current: bool = False
    location: str | None = None
    work_type: str | None = None
    description: str | None = None
    key_achievement: str | None = None
    tech_stack: list[str] = Field(default_factory=list)


class WorkExperienceUpdate(BaseModel):
    """Update a work experience entry. All fields optional."""

    company: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool | None = None
    location: str | None = None
    work_type: str | None = None
    description: str | None = None
    key_achievement: str | None = None
    tech_stack: list[str] | None = None


class WorkExperienceResponse(BaseModel):
    """Work experience API response."""

    id: uuid.UUID
    user_id: uuid.UUID
    company: str
    title: str
    start_date: str
    end_date: str | None = None
    is_current: bool = False
    location: str | None = None
    work_type: str | None = None
    description: str | None = None
    key_achievement: str | None = None
    tech_stack: list = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
