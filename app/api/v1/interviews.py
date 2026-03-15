"""Interviews API endpoints.

Referenced by file tree spec: app/api/v1/interviews.py
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, SuccessResponse
from app.schemas.interview import InterviewCreate, InterviewResponse, InterviewUpdate

router = APIRouter(prefix="/interviews")


@router.get("", response_model=DataResponse[list[InterviewResponse]])
async def list_interviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[InterviewResponse]]:
    """List all interviews for the current user."""
    raise NotImplementedError


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DataResponse[InterviewResponse])
async def create_interview(
    body: InterviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[InterviewResponse]:
    """Create a new interview record."""
    raise NotImplementedError


@router.get("/{interview_id}", response_model=DataResponse[InterviewResponse])
async def get_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[InterviewResponse]:
    """Get an interview by ID."""
    raise NotImplementedError


@router.put("/{interview_id}", response_model=DataResponse[InterviewResponse])
async def update_interview(
    interview_id: uuid.UUID,
    body: InterviewUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[InterviewResponse]:
    """Update an interview record (outcome, notes, ratings)."""
    raise NotImplementedError


@router.delete("/{interview_id}", response_model=SuccessResponse)
async def delete_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """Delete an interview record."""
    raise NotImplementedError
