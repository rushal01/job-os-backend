"""Education schemas — CRUD request/response models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EducationCreate(BaseModel):
    """Create an education entry."""

    institution: str = Field(..., max_length=255)
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: float | None = None
    show_gpa: bool = False


class EducationUpdate(BaseModel):
    """Update an education entry. All fields optional."""

    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: float | None = None
    show_gpa: bool | None = None


class EducationResponse(BaseModel):
    """Education API response."""

    id: uuid.UUID
    user_id: uuid.UUID
    institution: str
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: float | None = None
    show_gpa: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
