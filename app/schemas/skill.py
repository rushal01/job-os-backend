"""Skill schemas — CRUD request/response models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    """Create a skill."""

    name: str = Field(..., max_length=200)
    category: str = Field(..., max_length=50)
    proficiency: int = Field(..., ge=1, le=5)
    years_used: float | None = None
    last_used_date: str | None = None
    want_to_use: bool = True
    currently_learning: bool = False
    context: str | None = None


class SkillUpdate(BaseModel):
    """Update a skill. All fields optional."""

    name: str | None = None
    category: str | None = None
    proficiency: int | None = Field(None, ge=1, le=5)
    years_used: float | None = None
    last_used_date: str | None = None
    want_to_use: bool | None = None
    currently_learning: bool | None = None
    context: str | None = None


class SkillResponse(BaseModel):
    """Skill API response."""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    category: str
    proficiency: int
    years_used: float | None = None
    last_used_date: str | None = None
    want_to_use: bool = True
    currently_learning: bool = False
    context: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillBatchImport(BaseModel):
    """Batch import multiple skills."""

    skills: list[SkillCreate]
