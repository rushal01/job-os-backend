"""Application schemas — API Contract Section 4.5.

Defines request/response models for application tracking and submission.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ApplicationResponse(BaseModel):
    """Full application representation returned by API."""

    id: uuid.UUID
    job_id: uuid.UUID
    user_id: uuid.UUID
    profile_id: uuid.UUID
    status: str
    submitted_at: datetime | None = None
    submission_method: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    """Create a new application (internal use — auto-created from job pipeline)."""

    job_id: uuid.UUID
    profile_id: uuid.UUID


_VALID_APP_STATUSES = {
    "pending", "submitted", "screening", "interview",
    "offer", "rejected", "withdrawn",
}


class ApplicationStatusUpdate(BaseModel):
    """PUT /applications/:id/status request body."""

    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _VALID_APP_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {sorted(_VALID_APP_STATUSES)}")
        return v


class MarkAppliedRequest(BaseModel):
    """POST /applications/:id/mark-applied request body."""

    method: str
    notes: str | None = None


class ApplicationFilters(BaseModel):
    """Query filters for GET /applications."""

    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    status: str | None = None
    profile_id: uuid.UUID | None = None
