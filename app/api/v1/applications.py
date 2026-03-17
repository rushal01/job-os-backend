"""Applications API endpoints — API Contract Section 4.5.

6 endpoints: list, get, submit, mark-applied, status update, undo.
"""

import base64
import contextlib
import uuid
from datetime import UTC

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.application import Application
from app.models.user import User
from app.schemas.application import (
    ApplicationResponse,
    ApplicationStatusUpdate,
    MarkAppliedRequest,
)
from app.schemas.common import DataResponse, PaginatedResponse, TaskResponse

router = APIRouter(prefix="/applications")


@router.get("/stats", response_model=DataResponse[dict])
async def get_application_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Get application statistics for the current user."""
    from sqlalchemy import func

    base = select(Application.status, func.count(Application.id)).where(
        Application.user_id == current_user.id,
        Application.is_deleted == False,  # noqa: E712
    ).group_by(Application.status)
    result = await db.execute(base)
    by_status = {row[0]: row[1] for row in result.all()}

    total = sum(by_status.values())
    active = sum(by_status.get(s, 0) for s in ["pending", "submitted", "screening", "interview"])
    response_count = sum(by_status.get(s, 0) for s in ["screening", "interview", "offer", "rejected"])
    response_rate = round((response_count / total * 100) if total > 0 else 0.0, 1)

    return {"data": {
        "total": total,
        "by_status": by_status,
        "active": active,
        "response_rate": response_rate,
        "interviews": by_status.get("interview", 0),
        "offers": by_status.get("offer", 0),
        "rejected": by_status.get("rejected", 0),
    }}


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
    ).order_by(Application.updated_at.desc())

    if status:
        query = query.where(Application.status == status)

    if profile_id:
        query = query.where(Application.profile_id == profile_id)

    # Cursor pagination using offset (base64-encoded integer)
    if cursor:
        with contextlib.suppress(ValueError, Exception):
            cursor_offset = int(base64.b64decode(cursor).decode())
            query = query.offset(cursor_offset)

    # Fetch limit+1 to determine has_more
    query = query.limit(limit + 1)
    result = await db.execute(query)
    items = list(result.scalars().all())

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = None
    if has_more:
        current_offset = 0
        if cursor:
            with contextlib.suppress(ValueError, Exception):
                current_offset = int(base64.b64decode(cursor).decode())
        next_offset = current_offset + limit
        next_cursor = base64.b64encode(str(next_offset).encode()).decode()

    return {"data": items, "next_cursor": next_cursor, "has_more": has_more}


@router.get("/{application_id}/timeline", response_model=DataResponse[list[dict]])
async def get_application_timeline(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the activity timeline for an application."""
    result = await db.execute(
        select(ActivityLog).where(
            ActivityLog.entity_type == "application",
            ActivityLog.entity_id == application_id,
            ActivityLog.user_id == current_user.id,
        ).order_by(ActivityLog.created_at.desc())
    )
    entries = result.scalars().all()

    timeline = []
    for entry in entries:
        timeline.append({
            "id": str(entry.id),
            "action": entry.action,
            "actor": entry.actor,
            "detail": entry.detail,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        })

    return {"data": timeline}


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
    from app.models.task import Task
    from app.tasks.application_tasks import submit_application as celery_submit

    # Verify application exists
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

    task = Task(user_id=current_user.id, task_name="submit_application", status="pending", progress_pct=0.0)
    db.add(task)
    await db.flush()
    await db.refresh(task)

    celery_result = celery_submit.delay(str(current_user.id), str(application_id))
    task.celery_task_id = celery_result.id
    await db.commit()
    return TaskResponse(task_id=str(task.id))


@router.post("/{application_id}/mark-applied", response_model=DataResponse[ApplicationResponse])
async def mark_applied(
    application_id: uuid.UUID,
    body: MarkAppliedRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ApplicationResponse]:
    """Manually mark an application as applied."""
    from datetime import datetime

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
    app.submitted_at = datetime.now(UTC)
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
    """Undo the last status change on an application (revert to pending)."""
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

    app.status = "pending"
    app.submitted_at = None
    app.submission_method = None
    await db.commit()
    await db.refresh(app)
    return {"data": app}
