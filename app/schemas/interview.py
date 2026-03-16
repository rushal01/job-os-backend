"""Interview schemas.

Referenced by file tree spec: app/schemas/interview.py
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_VALID_ROUND_TYPES = {
    "phone_screen", "technical", "behavioral", "system_design",
    "hiring_manager", "panel", "onsite", "take_home", "final",
}


class InterviewCreate(BaseModel):
    """Create a new interview record."""

    application_id: uuid.UUID
    round_type: str = Field(..., max_length=50)

    @field_validator("round_type")
    @classmethod
    def validate_round_type(cls, v: str) -> str:
        if v not in _VALID_ROUND_TYPES:
            raise ValueError(f"Invalid round_type. Must be one of: {sorted(_VALID_ROUND_TYPES)}")
        return v
    scheduled_at: datetime | None = None
    platform: str | None = None
    meeting_link: str | None = None
    interviewer_name: str | None = None
    interviewer_title: str | None = None
    interviewer_linkedin: str | None = None


class InterviewUpdate(BaseModel):
    """Update an interview record."""

    scheduled_at: datetime | None = None
    platform: str | None = None
    meeting_link: str | None = None
    interviewer_name: str | None = None
    interviewer_title: str | None = None
    outcome: str | None = None
    difficulty_rating: int | None = Field(default=None, ge=1, le=5)
    performance_rating: int | None = Field(default=None, ge=1, le=5)
    questions_asked: str | None = None
    notes: str | None = None
    next_steps: str | None = None


class InterviewResponse(BaseModel):
    """Full interview returned by API."""

    id: uuid.UUID
    application_id: uuid.UUID
    user_id: uuid.UUID
    round_type: str
    scheduled_at: datetime | None = None
    platform: str | None = None
    meeting_link: str | None = None
    interviewer_name: str | None = None
    interviewer_title: str | None = None
    interviewer_linkedin: str | None = None
    outcome: str | None = None
    difficulty_rating: int | None = None
    performance_rating: int | None = None
    questions_asked: str | None = None
    notes: str | None = None
    next_steps: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
