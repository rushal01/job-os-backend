"""Interview service — CRUD and prep pack generation for interviews."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import Interview


async def list_interviews(db: AsyncSession, user_id: uuid.UUID) -> list[Interview]:
    """List all interviews for a user."""
    raise NotImplementedError


async def create_interview(db: AsyncSession, user_id: uuid.UUID, data: dict) -> Interview:
    """Create a new interview record."""
    raise NotImplementedError


async def get_interview(db: AsyncSession, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview | None:
    """Get an interview by ID."""
    raise NotImplementedError


async def update_interview(db: AsyncSession, user_id: uuid.UUID, interview_id: uuid.UUID, data: dict) -> Interview:
    """Update an interview (outcome, notes, ratings)."""
    raise NotImplementedError


async def delete_interview(db: AsyncSession, user_id: uuid.UUID, interview_id: uuid.UUID) -> None:
    """Delete an interview record."""
    raise NotImplementedError
