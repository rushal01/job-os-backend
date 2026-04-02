"""Interviews API endpoints.

Referenced by file tree spec: app/api/v1/interviews.py
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, SuccessResponse
from app.schemas.interview import InterviewCreate, InterviewResponse, InterviewUpdate
from app.services import interview_service

router = APIRouter(prefix="/interviews")


@router.get("", response_model=DataResponse[list[InterviewResponse]])
async def list_interviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all interviews for the current user."""
    interviews = await interview_service.list_interviews(db, current_user.id)
    return {"data": interviews}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DataResponse[InterviewResponse])
async def create_interview(
    body: InterviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new interview record."""
    interview = await interview_service.create_interview(
        db, current_user.id, body.model_dump()
    )
    return {"data": interview}


@router.get("/{interview_id}", response_model=DataResponse[InterviewResponse])
async def get_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get an interview by ID."""
    interview = await interview_service.get_interview(db, current_user.id, interview_id)
    if interview is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Interview not found")
    return {"data": interview}


@router.put("/{interview_id}", response_model=DataResponse[InterviewResponse])
async def update_interview(
    interview_id: uuid.UUID,
    body: InterviewUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update an interview record (outcome, notes, ratings)."""
    interview = await interview_service.update_interview(
        db, current_user.id, interview_id, body.model_dump(exclude_unset=True)
    )
    return {"data": interview}


@router.delete("/{interview_id}", response_model=SuccessResponse)
async def delete_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an interview record."""
    await interview_service.delete_interview(db, current_user.id, interview_id)
    return {"success": True}
