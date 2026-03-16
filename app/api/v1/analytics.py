"""Analytics API endpoints — API Contract Section 4.11.

7 endpoints: funnel, sources, rejections, ai-cost, dashboard-stats, weekly-report, export.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.application import Application
from app.models.job import Job
from app.models.job_source import JobSource
from app.models.review_queue import ReviewQueue
from app.models.user import User
from app.schemas.analytics import (
    AICostStats,
    DashboardStats,
    ExportRequest,
    FunnelData,
    RejectionStats,
    SourceStats,
    WeeklyReport,
)
from app.schemas.common import DataResponse

router = APIRouter(prefix="/analytics")


def _period_start(period: str) -> datetime:
    """Convert period string like '30d' or '7d' to a start datetime."""
    days = 30
    if period.endswith("d"):
        try:
            days = int(period[:-1])
        except ValueError:
            days = 30
    return datetime.now(timezone.utc) - timedelta(days=days)


@router.get("/funnel", response_model=DataResponse[FunnelData])
async def get_funnel(
    period: str = Query(default="30d"),
    profile_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[FunnelData]:
    """Get application funnel data."""
    start = _period_start(period)

    base = select(Job.status, func.count(Job.id)).where(
        Job.user_id == current_user.id,
        Job.is_deleted == False,  # noqa: E712
        Job.created_at >= start,
    )
    if profile_id:
        base = base.where(Job.profile_id == profile_id)
    base = base.group_by(Job.status)

    result = await db.execute(base)
    counts: dict[str, int] = {row[0]: row[1] for row in result.all()}

    return {"data": FunnelData(
        new=counts.get("new", 0),
        scored=counts.get("scored", 0),
        content_ready=counts.get("content_ready", 0),
        applied=counts.get("applied", 0),
        interview=counts.get("interview", 0),
        offer=counts.get("offer", 0),
        rejected=counts.get("rejected", 0),
    )}


@router.get("/sources", response_model=DataResponse[list[SourceStats]])
async def get_sources(
    period: str = Query(default="30d"),
    profile_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[SourceStats]]:
    """Get per-source statistics."""
    start = _period_start(period)

    # Count jobs found per source
    query = (
        select(JobSource.source, func.count(func.distinct(JobSource.job_id)))
        .join(Job, Job.id == JobSource.job_id)
        .where(
            Job.user_id == current_user.id,
            Job.is_deleted == False,  # noqa: E712
            Job.created_at >= start,
        )
    )
    if profile_id:
        query = query.where(Job.profile_id == profile_id)
    query = query.group_by(JobSource.source)

    result = await db.execute(query)
    source_jobs: dict[str, int] = {row[0]: row[1] for row in result.all()}

    # Count applications per source
    app_query = (
        select(JobSource.source, func.count(func.distinct(Application.id)))
        .join(Job, Job.id == JobSource.job_id)
        .join(Application, Application.job_id == Job.id)
        .where(
            Job.user_id == current_user.id,
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

    # Count interviews per source
    interview_query = (
        select(JobSource.source, func.count(func.distinct(Application.id)))
        .join(Job, Job.id == JobSource.job_id)
        .join(Application, Application.job_id == Job.id)
        .where(
            Job.user_id == current_user.id,
            Job.is_deleted == False,  # noqa: E712
            Application.is_deleted == False,  # noqa: E712
            Application.status == "interview",
            Job.created_at >= start,
        )
    )
    if profile_id:
        interview_query = interview_query.where(Job.profile_id == profile_id)
    interview_query = interview_query.group_by(JobSource.source)

    result = await db.execute(interview_query)
    source_interviews: dict[str, int] = {row[0]: row[1] for row in result.all()}

    all_sources = set(source_jobs) | set(source_apps)
    stats = []
    for source in sorted(all_sources):
        jobs_found = source_jobs.get(source, 0)
        apps_sent = source_apps.get(source, 0)
        interviews = source_interviews.get(source, 0)
        conversion = round((apps_sent / jobs_found * 100) if jobs_found > 0 else 0.0, 1)
        stats.append(SourceStats(
            source=source,
            jobs_found=jobs_found,
            applications_sent=apps_sent,
            interviews=interviews,
            conversion_rate=conversion,
        ))

    return {"data": stats}


@router.get("/rejections", response_model=DataResponse[RejectionStats])
async def get_rejections(
    period: str = Query(default="30d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[RejectionStats]:
    """Get rejection analysis."""
    start = _period_start(period)

    total = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
            Application.status == "rejected",
            Application.created_at >= start,
        )
    )).scalar() or 0

    return {"data": RejectionStats(
        total_rejections=total,
        by_stage={},
        common_reasons=[],
    )}


@router.get("/ai-cost", response_model=DataResponse[AICostStats])
async def get_ai_cost(
    period: str = Query(default="30d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AICostStats]:
    """Get AI usage cost breakdown."""
    return {"data": AICostStats(
        total_cost=0.0,
        by_provider={},
        by_task={},
        period=period,
    )}


@router.get("/dashboard-stats", response_model=DataResponse[DashboardStats])
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[DashboardStats]:
    """Get dashboard summary statistics."""
    now = datetime.now(timezone.utc)

    # Pending reviews
    pending_reviews = (await db.execute(
        select(func.count(ReviewQueue.id)).where(
            ReviewQueue.user_id == current_user.id,
            ReviewQueue.status == "pending",
        )
    )).scalar() or 0

    # Response rate
    total_apps = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
        )
    )).scalar() or 0

    responded_apps = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
            Application.status.in_(["screening", "interview", "offer", "rejected"]),
        )
    )).scalar() or 0

    response_rate = round((responded_apps / total_apps * 100) if total_apps > 0 else 0.0, 1)

    # Jobs discovered today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    jobs_today = (await db.execute(
        select(func.count(Job.id)).where(
            Job.user_id == current_user.id,
            Job.is_deleted == False,  # noqa: E712
            Job.created_at >= today_start,
        )
    )).scalar() or 0

    # Active applications (pending, submitted, screening, interview)
    active_applications = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
            Application.status.in_(["pending", "submitted", "screening", "interview"]),
        )
    )).scalar() or 0

    return {"data": DashboardStats(
        jobs_today=jobs_today,
        jobs_today_change=0.0,
        pending_reviews=pending_reviews,
        active_applications=active_applications,
        active_applications_change=0.0,
        response_rate=response_rate,
        response_rate_change=0.0,
    )}


@router.get("/weekly-report", response_model=DataResponse[WeeklyReport])
async def get_weekly_report(
    week: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[WeeklyReport]:
    """Get weekly report."""
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    week_label = week_start.strftime("%Y-W%W")

    if week:
        week_label = week

    jobs_discovered = (await db.execute(
        select(func.count(Job.id)).where(
            Job.user_id == current_user.id,
            Job.is_deleted == False,  # noqa: E712
            Job.created_at >= week_start,
            Job.created_at < week_end,
        )
    )).scalar() or 0

    applications_sent = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
            Application.created_at >= week_start,
            Application.created_at < week_end,
        )
    )).scalar() or 0

    interviews = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
            Application.status == "interview",
            Application.updated_at >= week_start,
            Application.updated_at < week_end,
        )
    )).scalar() or 0

    offers = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
            Application.status == "offer",
            Application.updated_at >= week_start,
            Application.updated_at < week_end,
        )
    )).scalar() or 0

    return {"data": WeeklyReport(
        week=week_label,
        jobs_discovered=jobs_discovered,
        applications_sent=applications_sent,
        interviews=interviews,
        offers=offers,
        highlights=[],
    )}


@router.post("/export")
async def export_analytics(
    body: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export analytics data as CSV/PDF."""
    raise NotImplementedError
