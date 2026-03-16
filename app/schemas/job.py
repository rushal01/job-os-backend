"""Job schemas — API Contract Section 4.3.

Defines request/response models for job listing, creation, scoring, and filtering.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ScoreBreakdown(BaseModel):
    """Detailed scoring breakdown for a job match."""

    skills_match: float | None = None
    seniority_match: float | None = None
    location_match: float | None = None
    salary_match: float | None = None
    company_match: float | None = None


class JobResponse(BaseModel):
    """Full job representation returned by API."""

    id: uuid.UUID
    user_id: uuid.UUID
    profile_id: uuid.UUID
    title: str
    company: str
    location: str | None = None
    location_type: str | None = None
    seniority: str | None = None
    employment_type: str | None = None
    description: str | None = None
    apply_url: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    score: float | None = None
    score_breakdown: dict | None = None
    confidence: float | None = None
    risk_score: float | None = None
    decision: str | None = None
    decision_reasoning: str | None = None
    skills_required: list = []
    skills_preferred: list = []
    skills_matched: list = []
    skills_missing: list = []
    status: str
    company_intel: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    """Manual job creation — POST /jobs/manual."""

    profile_id: uuid.UUID
    title: str = Field(..., max_length=500)
    company: str = Field(..., max_length=255)
    location: str | None = None
    location_type: str | None = None
    seniority: str | None = None
    employment_type: str | None = None
    description: str | None = None
    apply_url: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None


_VALID_JOB_STATUSES = {
    "new", "scored", "content_ready", "applied", "interview",
    "offer", "rejected", "skipped", "bookmarked", "ghosted",
}


class JobStatusUpdate(BaseModel):
    """PUT /jobs/:id/status request body."""

    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _VALID_JOB_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {sorted(_VALID_JOB_STATUSES)}")
        return v


class JobFilters(BaseModel):
    """Query filters for GET /jobs."""

    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    sort: str | None = None
    status: str | None = None
    min_score: float | None = None
    company: str | None = None
    profile_id: uuid.UUID | None = None


class BulkScoreRequest(BaseModel):
    """POST /jobs/bulk-score request body."""

    job_ids: list[uuid.UUID]


class DiscoverRequest(BaseModel):
    """POST /jobs/discover request body."""

    profile_id: uuid.UUID
