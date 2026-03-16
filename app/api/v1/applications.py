"""Applications API endpoints — API Contract Section 4.5.

6 endpoints: list, get, submit, mark-applied, status update, undo.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.application import Application
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
    query = select(Application).where(
        Application.user_id == current_user.id,
        Application.is_deleted == False,  # noqa: E712
    ).order_by(Application.updated_at.desc()).limit(limit)

    if status:
        query = query.where(Application.status == status)

    if profile_id:
        query = query.where(Application.profile_id == profile_id)

    result = await db.execute(query)
    items = result.scalars().all()

    return {"data": items, "next_cursor": None, "has_more": False}


@router.get("/{application_id}", response_model=DataResponse[ApplicationResponse])
async def get_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ApplicationResponse]:
    """Get a single application by ID."""
    result = await db.execute(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Application not found")
    return {"data": app}


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
    from datetime import datetime, timezone

    result = await db.execute(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Application not found")

    app.status = "submitted"
    app.submission_method = body.method
    app.submitted_at = datetime.now(timezone.utc)
    if body.notes:
        app.notes = body.notes

    await db.commit()
    await db.refresh(app)
    return {"data": app}


@router.put("/{application_id}/status", response_model=DataResponse[ApplicationResponse])
async def update_application_status(
    application_id: uuid.UUID,
    body: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ApplicationResponse]:
    """Update application status."""
    result = await db.execute(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Application not found")

    app.status = body.status
    await db.commit()
    await db.refresh(app)
    return {"data": app}


@router.post("/{application_id}/undo", response_model=DataResponse[ApplicationResponse])
async def undo_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ApplicationResponse]:
    """Undo the last status change on an application."""
    raise NotImplementedError
