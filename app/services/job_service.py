"""Job service — CRUD, status management, search, manual creation.

Implements business logic for job management per API Contract Section 4.3.
"""

import base64
import contextlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.job import JobCreate


async def list_jobs(
    db: AsyncSession,
    user_id: uuid.UUID,
    cursor: str | None,
    limit: int,
    sort: str | None,
    filters: dict,
) -> tuple[list[Job], str | None, bool]:
    """List jobs with cursor pagination and filters. Returns (jobs, next_cursor, has_more)."""
    query = select(Job).where(
        Job.user_id == user_id, Job.is_deleted == False  # noqa: E712
    )

    # Apply filters
    if filters.get("status"):
        query = query.where(Job.status == filters["status"])
    if filters.get("min_score") is not None:
        query = query.where(Job.score >= filters["min_score"])
    if filters.get("company"):
        query = query.where(Job.company.ilike(f"%{filters['company']}%"))
    if filters.get("profile_id"):
        query = query.where(Job.profile_id == filters["profile_id"])

    # Sort
    if sort == "score":
        query = query.order_by(Job.score.desc().nullslast(), Job.created_at.desc())
    elif sort == "company":
        query = query.order_by(Job.company, Job.created_at.desc())
    else:
        query = query.order_by(Job.created_at.desc())

    # Cursor pagination using offset (base64-encoded integer)
    if cursor:
        with contextlib.suppress(ValueError, Exception):
            cursor_offset = int(base64.b64decode(cursor).decode())
            query = query.offset(cursor_offset)

    # Fetch limit+1 to determine has_more
    query = query.limit(limit + 1)
    result = await db.execute(query)
    jobs = list(result.scalars().all())

    has_more = len(jobs) > limit
    if has_more:
        jobs = jobs[:limit]

    next_cursor = None
    if has_more:
        # Encode the offset for the next page
        current_offset = 0
        if cursor:
            with contextlib.suppress(ValueError, Exception):
                current_offset = int(base64.b64decode(cursor).decode())
        next_offset = current_offset + limit
        next_cursor = base64.b64encode(str(next_offset).encode()).decode()

    return jobs, next_cursor, has_more


async def get_job(
    db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID
) -> Job | None:
    """Get a job by ID, enforcing user ownership."""
    result = await db.execute(
        select(Job).where(
            Job.id == job_id,
            Job.user_id == user_id,
            Job.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def create_job_manual(
    db: AsyncSession, user_id: uuid.UUID, data: JobCreate
) -> Job:
    """Create a job manually with provided fields."""
    job = Job(
        user_id=user_id,
        profile_id=data.profile_id,
        title=data.title,
        company=data.company,
        location=data.location,
        location_type=data.location_type,
        seniority=data.seniority,
        employment_type=data.employment_type,
        description=data.description,
        apply_url=data.apply_url,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        salary_currency=data.salary_currency,
        status="new",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def update_job_status(
    db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID, new_status: str
) -> Job | None:
    """Update a job's status."""
    job = await get_job(db, user_id, job_id)
    if job is None:
        return None

    job.status = new_status
    await db.flush()
    await db.refresh(job)
    return job


async def bookmark_job(
    db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID
) -> Job | None:
    """Set job status to bookmarked."""
    return await update_job_status(db, user_id, job_id, "bookmarked")


async def skip_job(
    db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID
) -> Job | None:
    """Set job status to skipped."""
    return await update_job_status(db, user_id, job_id, "skipped")


async def search_jobs(
    db: AsyncSession, user_id: uuid.UUID, query: str, limit: int
) -> list[Job]:
    """Search jobs by title/company using LIKE (SQLite-compatible fallback).

    In production with PostgreSQL, this would use the tsvector search_vector index.
    """
    search_term = f"%{query}%"
    result = await db.execute(
        select(Job)
        .where(
            Job.user_id == user_id,
            Job.is_deleted == False,  # noqa: E712
            (Job.title.ilike(search_term) | Job.company.ilike(search_term)),
        )
        .order_by(Job.score.desc().nullslast())
        .limit(limit)
    )
    return list(result.scalars().all())
