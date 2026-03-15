"""Education service — CRUD operations."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.education import Education
from app.schemas.education import EducationCreate, EducationUpdate


async def list_education(db: AsyncSession, user_id: uuid.UUID) -> list[Education]:
    """List all education entries for a user."""
    result = await db.execute(
        select(Education)
        .where(Education.user_id == user_id)
        .order_by(Education.end_date.desc().nullslast())
    )
    return list(result.scalars().all())


async def create_education(
    db: AsyncSession, user_id: uuid.UUID, data: EducationCreate
) -> Education:
    """Create a new education entry."""
    edu = Education(user_id=user_id, **data.model_dump(exclude_none=True))
    db.add(edu)
    await db.flush()
    await db.refresh(edu)
    return edu


async def get_education(
    db: AsyncSession, user_id: uuid.UUID, edu_id: uuid.UUID
) -> Education | None:
    """Get an education entry by ID, enforcing user ownership."""
    result = await db.execute(
        select(Education).where(
            Education.id == edu_id, Education.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def update_education(
    db: AsyncSession, user_id: uuid.UUID, edu_id: uuid.UUID, data: EducationUpdate
) -> Education | None:
    """Update an education entry."""
    edu = await get_education(db, user_id, edu_id)
    if edu is None:
        return None

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(edu, field, value)

    await db.flush()
    await db.refresh(edu)
    return edu


async def delete_education(
    db: AsyncSession, user_id: uuid.UUID, edu_id: uuid.UUID
) -> bool:
    """Delete an education entry. Returns True if found."""
    edu = await get_education(db, user_id, edu_id)
    if edu is None:
        return False

    await db.delete(edu)
    await db.flush()
    return True
