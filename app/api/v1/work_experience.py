"""Work experience API endpoints — CRUD."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, SuccessResponse
from app.schemas.work_experience import (
    WorkExperienceCreate,
    WorkExperienceResponse,
    WorkExperienceUpdate,
)
from app.services import work_experience_service

router = APIRouter(prefix="/work-experience")


@router.get("", response_model=DataResponse[list[WorkExperienceResponse]])
async def list_work_experiences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all work experiences for the current user."""
    items = await work_experience_service.list_work_experiences(db, current_user.id)
    return {"data": items}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DataResponse[WorkExperienceResponse],
)
async def create_work_experience(
    body: WorkExperienceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new work experience entry."""
    exp = await work_experience_service.create_work_experience(
        db, current_user.id, body
    )
    return {"data": exp}


@router.get("/{exp_id}", response_model=DataResponse[WorkExperienceResponse])
async def get_work_experience(
    exp_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a work experience entry by ID."""
    exp = await work_experience_service.get_work_experience(
        db, current_user.id, exp_id
    )
    if exp is None:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Work experience not found"
        )
    return {"data": exp}


@router.put("/{exp_id}", response_model=DataResponse[WorkExperienceResponse])
async def update_work_experience(
    exp_id: uuid.UUID,
    body: WorkExperienceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a work experience entry."""
    exp = await work_experience_service.update_work_experience(
        db, current_user.id, exp_id, body
    )
    if exp is None:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Work experience not found"
        )
    return {"data": exp}


@router.delete("/{exp_id}", response_model=SuccessResponse)
async def delete_work_experience(
    exp_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a work experience entry."""
    found = await work_experience_service.delete_work_experience(
        db, current_user.id, exp_id
    )
    if not found:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Work experience not found"
        )
    return {"success": True}
