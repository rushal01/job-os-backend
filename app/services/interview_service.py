"""Interview service — CRUD and prep pack generation for interviews."""

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.models.interview import Interview


async def list_interviews(db: AsyncSession, user_id: uuid.UUID) -> list[Interview]:
    """List all interviews for a user."""
    result = await db.execute(
        select(Interview)
        .where(Interview.user_id == user_id)
        .order_by(Interview.scheduled_at.desc().nullslast())
    )
    return list(result.scalars().all())


async def create_interview(db: AsyncSession, user_id: uuid.UUID, data: dict) -> Interview:
    """Create a new interview record."""
    interview = Interview(user_id=user_id, **data)
    db.add(interview)
    await db.flush()
    await db.refresh(interview)
    logger.info("Created interview {} for user {}", interview.id, user_id)
    return interview


async def get_interview(db: AsyncSession, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview | None:
    """Get an interview by ID."""
    result = await db.execute(
        select(Interview).where(
            Interview.id == interview_id,
            Interview.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_interview(db: AsyncSession, user_id: uuid.UUID, interview_id: uuid.UUID, data: dict) -> Interview:
    """Update an interview (outcome, notes, ratings)."""
    interview = await get_interview(db, user_id, interview_id)
    if interview is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Interview not found")

    for key, value in data.items():
        if value is not None:
            setattr(interview, key, value)

    await db.flush()
    await db.refresh(interview)
    logger.info("Updated interview {} for user {}", interview_id, user_id)
    return interview


async def delete_interview(db: AsyncSession, user_id: uuid.UUID, interview_id: uuid.UUID) -> None:
    """Delete an interview record."""
    interview = await get_interview(db, user_id, interview_id)
    if interview is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Interview not found")

    await db.delete(interview)
    await db.flush()
    logger.info("Deleted interview {} for user {}", interview_id, user_id)
