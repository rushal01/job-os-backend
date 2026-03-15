"""Profile API endpoints — API Contract Section 4.2.

8 endpoints: list, create, get, update, delete, clone, activate, completeness.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, SuccessResponse
from app.schemas.profile import (
    CloneRequest,
    ProfileCompleteness,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)
from app.services import profile_service

router = APIRouter(prefix="/profiles")


@router.get("", response_model=DataResponse[list[ProfileResponse]])
async def list_profiles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all profiles for the current user."""
    profiles = await profile_service.list_profiles(db, current_user.id)
    return {"data": profiles}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DataResponse[ProfileResponse],
)
async def create_profile(
    body: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new profile."""
    profile = await profile_service.create_profile(db, current_user.id, body)
    return {"data": profile}


@router.get("/{profile_id}", response_model=DataResponse[ProfileResponse])
async def get_profile(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a profile by ID."""
    profile = await profile_service.get_profile(db, current_user.id, profile_id)
    if profile is None:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Profile not found"
        )
    return {"data": profile}


@router.put("/{profile_id}", response_model=DataResponse[ProfileResponse])
async def update_profile(
    profile_id: uuid.UUID,
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a profile."""
    profile = await profile_service.update_profile(
        db, current_user.id, profile_id, body
    )
    if profile is None:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Profile not found"
        )
    return {"data": profile}


@router.delete("/{profile_id}", response_model=SuccessResponse)
async def delete_profile(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Soft-delete a profile."""
    found = await profile_service.delete_profile(db, current_user.id, profile_id)
    if not found:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Profile not found"
        )
    return {"success": True}


@router.post(
    "/{profile_id}/clone",
    status_code=status.HTTP_201_CREATED,
    response_model=DataResponse[ProfileResponse],
)
async def clone_profile(
    profile_id: uuid.UUID,
    body: CloneRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Clone a profile with selected data types."""
    profile = await profile_service.clone_profile(
        db, current_user.id, profile_id, body.name, body.data_types
    )
    if profile is None:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Source profile not found"
        )
    return {"data": profile}


@router.put("/{profile_id}/activate", response_model=DataResponse[ProfileResponse])
async def activate_profile(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set a profile as the active profile (deactivates others)."""
    profile = await profile_service.activate_profile(
        db, current_user.id, profile_id
    )
    if profile is None:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Profile not found"
        )
    return {"data": profile}


@router.get("/{profile_id}/completeness", response_model=ProfileCompleteness)
async def get_completeness(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Calculate and return profile completeness percentage."""
    profile = await profile_service.get_profile(db, current_user.id, profile_id)
    if profile is None:
        raise AppError(
            code=ErrorCode.RESOURCE_NOT_FOUND, message="Profile not found"
        )
    pct, missing = profile_service.compute_completeness(profile)
    return {"pct": pct, "missing_items": missing}
