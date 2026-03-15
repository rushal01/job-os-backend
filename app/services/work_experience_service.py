"""Work experience service — CRUD operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_experience import WorkExperience
from app.schemas.work_experience import WorkExperienceCreate, WorkExperienceUpdate


async def list_work_experiences(
    db: AsyncSession, user_id: uuid.UUID
) -> list[WorkExperience]:
    """List all work experiences for a user, most recent first."""
    result = await db.execute(
        select(WorkExperience)
        .where(WorkExperience.user_id == user_id)
        .order_by(WorkExperience.is_current.desc(), WorkExperience.start_date.desc())
    )
    return list(result.scalars().all())


async def create_work_experience(
    db: AsyncSession, user_id: uuid.UUID, data: WorkExperienceCreate
) -> WorkExperience:
    """Create a new work experience entry."""
    exp = WorkExperience(user_id=user_id, **data.model_dump())
    db.add(exp)
    await db.flush()
    await db.refresh(exp)
    return exp


async def get_work_experience(
    db: AsyncSession, user_id: uuid.UUID, exp_id: uuid.UUID
) -> WorkExperience | None:
    """Get a work experience by ID, enforcing user ownership."""
    result = await db.execute(
        select(WorkExperience).where(
            WorkExperience.id == exp_id, WorkExperience.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def update_work_experience(
    db: AsyncSession,
    user_id: uuid.UUID,
    exp_id: uuid.UUID,
    data: WorkExperienceUpdate,
) -> WorkExperience | None:
    """Update a work experience entry."""
    exp = await get_work_experience(db, user_id, exp_id)
    if exp is None:
        return None

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(exp, field, value)

    await db.flush()
    await db.refresh(exp)
    return exp


async def delete_work_experience(
    db: AsyncSession, user_id: uuid.UUID, exp_id: uuid.UUID
) -> bool:
    """Delete a work experience entry. Returns True if found."""
    exp = await get_work_experience(db, user_id, exp_id)
    if exp is None:
        return False

    await db.delete(exp)
    await db.flush()
    return True
