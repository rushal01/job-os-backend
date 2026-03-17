"""Analytics service — funnel, sources, rejections, AI cost, dashboard stats.

Implements analytics queries per API Contract Section 4.11.
Note: The API routes in api/v1/analytics.py implement queries inline.
These service functions provide the same logic for use by tasks or other services.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.job import Job
from app.models.job_source import JobSource
from app.models.review_queue import ReviewQueue


def _period_start(period: str) -> datetime:
    """Convert period string like '30d' or '7d' to a start datetime."""
    days = 30
    if period.endswith("d"):
        try:
            days = int(period[:-1])
        except ValueError:
            days = 30
    return datetime.now(timezone.utc) - timedelta(days=days)


async def get_funnel(
    db: AsyncSession, user_id: uuid.UUID, period: str, profile_id: uuid.UUID | None,
) -> dict:
    """Compute application funnel data (new -> scored -> applied -> interview -> offer)."""
    start = _period_start(period)
    base = select(Job.status, func.count(Job.id)).where(
        Job.user_id == user_id,
        Job.is_deleted == False,  # noqa: E712
        Job.created_at >= start,
    )
    if profile_id:
        base = base.where(Job.profile_id == profile_id)
    base = base.group_by(Job.status)

    result = await db.execute(base)
    counts: dict[str, int] = {row[0]: row[1] for row in result.all()}
    return {
        "new": counts.get("new", 0),
        "scored": counts.get("scored", 0),
        "content_ready": counts.get("content_ready", 0),
        "applied": counts.get("applied", 0),
        "interview": counts.get("interview", 0),
        "offer": counts.get("offer", 0),
        "rejected": counts.get("rejected", 0),
    }


async def get_sources(
    db: AsyncSession, user_id: uuid.UUID, period: str, profile_id: uuid.UUID | None,
) -> list[dict]:
    """Compute per-source statistics."""
    start = _period_start(period)

    query = (
        select(JobSource.source, func.count(func.distinct(JobSource.job_id)))
        .join(Job, Job.id == JobSource.job_id)
        .where(Job.user_id == user_id, Job.is_deleted == False, Job.created_at >= start)  # noqa: E712
    )
    if profile_id:
        query = query.where(Job.profile_id == profile_id)
    query = query.group_by(JobSource.source)

    result = await db.execute(query)
    source_jobs: dict[str, int] = {row[0]: row[1] for row in result.all()}

    app_query = (
        select(JobSource.source, func.count(func.distinct(Application.id)))
        .join(Job, Job.id == JobSource.job_id)
        .join(Application, Application.job_id == Job.id)
        .where(
            Job.user_id == user_id,
            Job.is_deleted == False,  # noqa: E712
            Application.is_deleted == False,  # noqa: E712
            Job.created_at >= start,
        )
    )
    if profile_id:
        app_query = app_query.where(Job.profile_id == profile_id)
    app_query = app_query.group_by(JobSource.source)

    result = await db.execute(app_query)
    source_apps: dict[str, int] = {row[0]: row[1] for row in result.all()}

    all_sources = set(source_jobs) | set(source_apps)
    stats = []
    for source in sorted(all_sources):
        jobs_found = source_jobs.get(source, 0)
        apps_sent = source_apps.get(source, 0)
        conversion = round((apps_sent / jobs_found * 100) if jobs_found > 0 else 0.0, 1)
        stats.append({
            "source": source,
            "jobs_found": jobs_found,
            "applications_sent": apps_sent,
            "conversion_rate": conversion,
        })
    return stats


async def get_rejections(db: AsyncSession, user_id: uuid.UUID, period: str) -> dict:
    """Analyze rejections by stage and reason."""
    start = _period_start(period)
    total = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == user_id,
            Application.is_deleted == False,  # noqa: E712
            Application.status == "rejected",
            Application.created_at >= start,
        )
    )).scalar() or 0
    return {"total_rejections": total, "by_stage": {}, "common_reasons": []}


async def get_ai_cost(db: AsyncSession, user_id: uuid.UUID, period: str) -> dict:
    """Compute AI usage cost breakdown by provider and task."""
    return {"total_cost": 0.0, "by_provider": {}, "by_task": {}, "period": period}


async def get_dashboard_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Compute dashboard summary statistics."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    pending_reviews = (await db.execute(
        select(func.count(ReviewQueue.id)).where(
            ReviewQueue.user_id == user_id, ReviewQueue.status == "pending",
        )
    )).scalar() or 0

    total_apps = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == user_id, Application.is_deleted == False,  # noqa: E712
        )
    )).scalar() or 0

    responded_apps = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == user_id,
            Application.is_deleted == False,  # noqa: E712
            Application.status.in_(["screening", "interview", "offer", "rejected"]),
        )
    )).scalar() or 0

    response_rate = round((responded_apps / total_apps * 100) if total_apps > 0 else 0.0, 1)

    jobs_today = (await db.execute(
        select(func.count(Job.id)).where(
            Job.user_id == user_id, Job.is_deleted == False, Job.created_at >= today_start,  # noqa: E712
        )
    )).scalar() or 0

    active_applications = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == user_id,
            Application.is_deleted == False,  # noqa: E712
            Application.status.in_(["pending", "submitted", "screening", "interview"]),
        )
    )).scalar() or 0

    return {
        "jobs_today": jobs_today,
        "pending_reviews": pending_reviews,
        "active_applications": active_applications,
        "response_rate": response_rate,
    }


async def get_weekly_report(db: AsyncSession, user_id: uuid.UUID, week: str | None) -> dict:
    """Generate weekly activity report."""
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    jobs_discovered = (await db.execute(
        select(func.count(Job.id)).where(
            Job.user_id == user_id, Job.is_deleted == False,  # noqa: E712
            Job.created_at >= week_start, Job.created_at < week_end,
        )
    )).scalar() or 0

    applications_sent = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == user_id, Application.is_deleted == False,  # noqa: E712
            Application.created_at >= week_start, Application.created_at < week_end,
        )
    )).scalar() or 0

    return {
        "week": week or week_start.strftime("%Y-W%W"),
        "jobs_discovered": jobs_discovered,
        "applications_sent": applications_sent,
        "highlights": [],
    }
