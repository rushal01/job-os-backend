"""Education API endpoints — CRUD."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, SuccessResponse
from app.schemas.education import EducationCreate, EducationResponse, EducationUpdate
from app.services import education_service

router = APIRouter(prefix="/education")


@router.get("", response_model=DataResponse[list[EducationResponse]])
async def list_education(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all education entries for the current user."""
    items = await education_service.list_education(db, current_user.id)
    return {"data": items}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DataResponse[EducationResponse],
)
async def create_education(
    body: EducationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new education entry."""
    edu = await education_service.create_education(db, current_user.id, body)
    return {"data": edu}


@router.get("/{edu_id}", response_model=DataResponse[EducationResponse])
async def get_education(
    edu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get an education entry by ID."""
    edu = await education_service.get_education(db, current_user.id, edu_id)
    if edu is None:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Education not found"
        )
    return {"data": edu}


@router.put("/{edu_id}", response_model=DataResponse[EducationResponse])
async def update_education(
    edu_id: uuid.UUID,
    body: EducationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update an education entry."""
    edu = await education_service.update_education(db, current_user.id, edu_id, body)
    if edu is None:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Education not found"
        )
    return {"data": edu}


@router.delete("/{edu_id}", response_model=SuccessResponse)
async def delete_education(
    edu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an education entry."""
    found = await education_service.delete_education(db, current_user.id, edu_id)
    if not found:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Education not found"
        )
    return {"success": True}
