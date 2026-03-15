"""Skill service — CRUD + batch import."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import Skill
from app.schemas.skill import SkillCreate, SkillUpdate


async def list_skills(db: AsyncSession, user_id: uuid.UUID) -> list[Skill]:
    """List all skills for a user."""
    result = await db.execute(
        select(Skill)
        .where(Skill.user_id == user_id)
        .order_by(Skill.category, Skill.name)
    )
    return list(result.scalars().all())


async def create_skill(
    db: AsyncSession, user_id: uuid.UUID, data: SkillCreate
) -> Skill:
    """Create a new skill."""
    skill = Skill(user_id=user_id, **data.model_dump())
    db.add(skill)
    await db.flush()
    await db.refresh(skill)
    return skill


async def get_skill(
    db: AsyncSession, user_id: uuid.UUID, skill_id: uuid.UUID
) -> Skill | None:
    """Get a skill by ID, enforcing user ownership."""
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_skill(
    db: AsyncSession, user_id: uuid.UUID, skill_id: uuid.UUID, data: SkillUpdate
) -> Skill | None:
    """Update a skill."""
    skill = await get_skill(db, user_id, skill_id)
    if skill is None:
        return None

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(skill, field, value)

    await db.flush()
    await db.refresh(skill)
    return skill


async def delete_skill(
    db: AsyncSession, user_id: uuid.UUID, skill_id: uuid.UUID
) -> bool:
    """Delete a skill. Returns True if found."""
    skill = await get_skill(db, user_id, skill_id)
    if skill is None:
        return False

    await db.delete(skill)
    await db.flush()
    return True


async def batch_import_skills(
    db: AsyncSession, user_id: uuid.UUID, skills_data: list[SkillCreate]
) -> list[Skill]:
    """Batch import multiple skills."""
    created = []
    for data in skills_data:
        skill = Skill(user_id=user_id, **data.model_dump())
        db.add(skill)
        created.append(skill)

    await db.flush()
    for skill in created:
        await db.refresh(skill)
    return created
