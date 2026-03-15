"""Applications API endpoints — API Contract Section 4.5.

6 endpoints: list, get, submit, mark-applied, status update, undo.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.application import (
    ApplicationResponse,
    ApplicationStatusUpdate,
    MarkAppliedRequest,
)
from app.schemas.common import DataResponse, PaginatedResponse, TaskResponse

router = APIRouter(prefix="/applications")


@router.get("", response_model=PaginatedResponse[ApplicationResponse])
async def list_applications(
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    profile_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ApplicationResponse]:
    """List applications with cursor pagination."""
    raise NotImplementedError


@router.get("/{application_id}", response_model=DataResponse[ApplicationResponse])
async def get_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ApplicationResponse]:
    """Get a single application by ID."""
    raise NotImplementedError


@router.post("/{application_id}/submit", response_model=TaskResponse)
async def submit_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Trigger async ATS auto-submission for an application."""
    raise NotImplementedError


@router.post("/{application_id}/mark-applied", response_model=DataResponse[ApplicationResponse])
async def mark_applied(
    application_id: uuid.UUID,
    body: MarkAppliedRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ApplicationResponse]:
    """Manually mark an application as applied."""
    raise NotImplementedError


@router.put("/{application_id}/status", response_model=DataResponse[ApplicationResponse])
async def update_application_status(
    application_id: uuid.UUID,
    body: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ApplicationResponse]:
    """Update application status."""
    raise NotImplementedError


@router.post("/{application_id}/undo", response_model=DataResponse[ApplicationResponse])
async def undo_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ApplicationResponse]:
    """Undo the last status change on an application."""
    raise NotImplementedError
