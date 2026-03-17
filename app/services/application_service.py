"""Application service — tracking, submission, and status management.

Implements business logic for application tracking per API Contract Section 4.5.
Note: The API routes in api/v1/applications.py implement most operations inline.
These service functions provide the same logic for use by tasks or other services.
"""

import base64
import uuid
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.models.application import Application


async def list_applications(
    db: AsyncSession,
    user_id: uuid.UUID,
    cursor: str | None,
    limit: int,
    filters: dict,
) -> tuple[list[Application], str | None, bool]:
    """List applications with cursor pagination. Returns (apps, next_cursor, has_more)."""
    query = select(Application).where(
        Application.user_id == user_id,
        Application.is_deleted == False,  # noqa: E712
    ).order_by(Application.updated_at.desc())

    if filters.get("status"):
        query = query.where(Application.status == filters["status"])
    if filters.get("profile_id"):
        query = query.where(Application.profile_id == filters["profile_id"])

    offset = 0
    if cursor:
        try:
            offset = int(base64.b64decode(cursor).decode())
        except Exception:
            offset = 0

    query = query.offset(offset).limit(limit + 1)
    result = await db.execute(query)
    items = list(result.scalars().all())

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = None
    if has_more:
        next_cursor = base64.b64encode(str(offset + limit).encode()).decode()

    return items, next_cursor, has_more


async def get_application(
    db: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID,
) -> Application | None:
    """Get an application by ID, enforcing user ownership."""
    result = await db.execute(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
            Application.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def submit_application(
    db: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID,
) -> str:
    """Queue ATS auto-submission via Celery. Returns task_id."""
    from app.models.task import Task
    from app.tasks.application_tasks import submit_application as celery_submit

    app = await get_application(db, user_id, application_id)
    if not app:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Application not found")

    task = Task(user_id=user_id, task_name="submit_application", status="pending", progress_pct=0.0)
    db.add(task)
    await db.flush()
    await db.refresh(task)

    celery_result = celery_submit.delay(str(user_id), str(application_id))
    task.celery_task_id = celery_result.id
    await db.flush()

    logger.info(f"Queued submission for application {application_id}, task {task.id}")
    return str(task.id)


async def mark_applied(
    db: AsyncSession,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
    method: str,
    notes: str | None,
) -> Application:
    """Manually mark an application as applied."""
    app = await get_application(db, user_id, application_id)
    if not app:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Application not found")

    app.status = "submitted"
    app.submission_method = method
    app.submitted_at = datetime.now(timezone.utc)
    if notes:
        app.notes = notes

    await db.flush()
    logger.info(f"Marked application {application_id} as applied via {method}")
    return app


async def update_status(
    db: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID, status: str,
) -> Application:
    """Update application status."""
    app = await get_application(db, user_id, application_id)
    if not app:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Application not found")

    app.status = status
    await db.flush()
    logger.info(f"Updated application {application_id} status to {status}")
    return app


async def undo_application(
    db: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID,
) -> Application:
    """Undo the last status change (revert to pending)."""
    app = await get_application(db, user_id, application_id)
    if not app:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Application not found")

    app.status = "pending"
    app.submitted_at = None
    app.submission_method = None
    await db.flush()
    logger.info(f"Undid application {application_id}, reverted to pending")
    return app
