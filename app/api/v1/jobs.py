"""Jobs API endpoints — API Contract Section 4.3.

11 endpoints: list, get, manual create, status update, bookmark, skip,
score, generate, bulk-score, search, discover.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, PaginatedResponse, TaskResponse
from app.schemas.job import (
    BulkScoreRequest,
    DiscoverRequest,
    JobCreate,
    JobResponse,
    JobStatusUpdate,
)
from app.services import job_service

router = APIRouter(prefix="/jobs")


@router.get("", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    sort: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    min_score: float | None = None,
    company: str | None = None,
    profile_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List jobs with cursor pagination and filters."""
    filters = {}
    if status_filter:
        filters["status"] = status_filter
    if min_score is not None:
        filters["min_score"] = min_score
    if company:
        filters["company"] = company
    if profile_id:
        filters["profile_id"] = profile_id

    jobs, next_cursor, has_more = await job_service.list_jobs(
        db, current_user.id, cursor, limit, sort, filters
    )
    return {"data": jobs, "next_cursor": next_cursor, "has_more": has_more}


@router.get("/search", response_model=DataResponse[list[JobResponse]])
async def search_jobs(
    q: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Full-text search across jobs."""
    jobs = await job_service.search_jobs(db, current_user.id, q, limit)
    return {"data": jobs}


@router.get("/{job_id}", response_model=DataResponse[JobResponse])
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single job by ID."""
    job = await job_service.get_job(db, current_user.id, job_id)
    if job is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Job not found")
    return {"data": job}


@router.post(
    "/manual",
    status_code=status.HTTP_201_CREATED,
    response_model=DataResponse[JobResponse],
)
async def create_job_manual(
    body: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually add a job."""
    job = await job_service.create_job_manual(db, current_user.id, body)
    return {"data": job}


@router.put("/{job_id}/status", response_model=DataResponse[JobResponse])
async def update_job_status(
    job_id: uuid.UUID,
    body: JobStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a job's status."""
    job = await job_service.update_job_status(
        db, current_user.id, job_id, body.status
    )
    if job is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Job not found")
    return {"data": job}


@router.post("/{job_id}/bookmark", response_model=DataResponse[JobResponse])
async def bookmark_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bookmark a job."""
    job = await job_service.bookmark_job(db, current_user.id, job_id)
    if job is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Job not found")
    return {"data": job}


@router.post("/{job_id}/skip", response_model=DataResponse[JobResponse])
async def skip_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Skip a job."""
    job = await job_service.skip_job(db, current_user.id, job_id)
    if job is None:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Job not found")
    return {"data": job}


@router.post("/{job_id}/score", response_model=TaskResponse)
async def score_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Trigger async scoring for a single job."""
    from app.models.task import Task
    from app.tasks.scoring_tasks import score_job as celery_score

    task = Task(user_id=current_user.id, task_name="score_job", status="pending", progress_pct=0.0)
    db.add(task)
    await db.flush()
    await db.refresh(task)

    result = celery_score.delay(str(current_user.id), str(job_id))
    task.celery_task_id = result.id
    await db.commit()
    return TaskResponse(task_id=str(task.id))


@router.post("/{job_id}/generate", response_model=TaskResponse)
async def generate_content_for_job(
    job_id: uuid.UUID,
    instructions: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Trigger async content generation for a job."""
    # Get active profile for user
    from sqlalchemy import select

    from app.models.profile import Profile
    from app.services.content_service import generate_resume
    result = await db.execute(
        select(Profile).where(
            Profile.user_id == current_user.id,
            Profile.is_active == True,  # noqa: E712
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="No active profile found")

    task_id = await generate_resume(db, current_user.id, job_id, profile.id, instructions)
    await db.commit()
    return TaskResponse(task_id=task_id)


@router.post("/bulk-score", response_model=TaskResponse)
async def bulk_score_jobs(
    body: BulkScoreRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Trigger bulk async scoring for multiple jobs."""
    from app.services.scoring_service import bulk_score_jobs as do_bulk_score

    task_id = await do_bulk_score(db, current_user.id, body.job_ids)
    await db.commit()
    return TaskResponse(task_id=task_id)


@router.post("/discover", response_model=TaskResponse)
async def discover_jobs(
    body: DiscoverRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Trigger async job discovery for a profile."""
    from app.models.task import Task
    from app.tasks.discovery_tasks import discover_jobs as celery_discover

    task = Task(
        user_id=current_user.id, task_name="discover_jobs", status="pending", progress_pct=0.0,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    result = celery_discover.delay(str(current_user.id), str(body.profile_id))
    task.celery_task_id = result.id
    await db.commit()
    return TaskResponse(task_id=str(task.id))
