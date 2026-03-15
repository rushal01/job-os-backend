"""Skill API endpoints — CRUD + batch import."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, SuccessResponse
from app.schemas.skill import SkillBatchImport, SkillCreate, SkillResponse, SkillUpdate
from app.services import skill_service

router = APIRouter(prefix="/skills")


@router.get("", response_model=DataResponse[list[SkillResponse]])
async def list_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all skills for the current user."""
    skills = await skill_service.list_skills(db, current_user.id)
    return {"data": skills}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DataResponse[SkillResponse],
)
async def create_skill(
    body: SkillCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new skill."""
    skill = await skill_service.create_skill(db, current_user.id, body)
    return {"data": skill}


@router.get("/{skill_id}", response_model=DataResponse[SkillResponse])
async def get_skill(
    skill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a skill by ID."""
    skill = await skill_service.get_skill(db, current_user.id, skill_id)
    if skill is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Skill not found")
    return {"data": skill}


@router.put("/{skill_id}", response_model=DataResponse[SkillResponse])
async def update_skill(
    skill_id: uuid.UUID,
    body: SkillUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a skill."""
    skill = await skill_service.update_skill(db, current_user.id, skill_id, body)
    if skill is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Skill not found")
    return {"data": skill}


@router.delete("/{skill_id}", response_model=SuccessResponse)
async def delete_skill(
    skill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a skill."""
    found = await skill_service.delete_skill(db, current_user.id, skill_id)
    if not found:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Skill not found")
    return {"success": True}


@router.post(
    "/batch",
    status_code=status.HTTP_201_CREATED,
    response_model=DataResponse[list[SkillResponse]],
)
async def batch_import_skills(
    body: SkillBatchImport,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Batch import multiple skills."""
    skills = await skill_service.batch_import_skills(
        db, current_user.id, body.skills
    )
    return {"data": skills}
