"""Analytics API endpoints — API Contract Section 4.11.

7 endpoints: funnel, sources, rejections, ai-cost, dashboard-stats, weekly-report, export.
"""

import uuid
from datetime import UTC, datetime, timedelta

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
    return datetime.now(UTC) - timedelta(days=days)


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
    now = datetime.now(UTC)

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
    now = datetime.now(UTC)
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


@router.get("/goals", response_model=DataResponse[list[dict]])
async def get_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[dict]]:
    """Get goal tracking data."""
    now = datetime.now(UTC)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    apps_this_week = (await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
            Application.created_at >= week_start,
        )
    )).scalar() or 0

    jobs_this_week = (await db.execute(
        select(func.count(Job.id)).where(
            Job.user_id == current_user.id,
            Job.is_deleted == False,  # noqa: E712
            Job.created_at >= week_start,
        )
    )).scalar() or 0

    user_settings = current_user.settings or {}
    goals = user_settings.get("goals", {})
    weekly_app_goal = goals.get("weekly_applications", 10)
    weekly_discovery_goal = goals.get("weekly_discoveries", 50)

    return {"data": [
        {"id": "weekly_applications", "name": "Weekly Applications", "current": apps_this_week, "target": weekly_app_goal, "status": "on_track" if apps_this_week >= weekly_app_goal * 0.5 else "behind"},
        {"id": "weekly_discoveries", "name": "Weekly Discoveries", "current": jobs_this_week, "target": weekly_discovery_goal, "status": "on_track" if jobs_this_week >= weekly_discovery_goal * 0.5 else "behind"},
        {"id": "response_rate", "name": "Response Rate %", "current": 0, "target": goals.get("response_rate", 20), "status": "behind"},
        {"id": "interviews", "name": "Weekly Interviews", "current": 0, "target": goals.get("weekly_interviews", 3), "status": "behind"},
    ]}


@router.get("/ab-tests", response_model=DataResponse[list[dict]])
async def get_ab_tests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[dict]]:
    """Get A/B test results for resume/CL variants."""
    from app.models.document import Document

    # Get documents with variant labels
    result = await db.execute(
        select(
            Document.variant_label,
            func.count(Document.id),
            func.avg(Document.quality_score),
        ).where(
            Document.user_id == current_user.id,
            Document.variant_label.isnot(None),
        ).group_by(Document.variant_label)
    )

    tests = []
    for label, count, avg_score in result.all():
        tests.append({
            "variant": label,
            "documents_generated": count,
            "avg_quality_score": round(float(avg_score or 0), 1),
        })

    return {"data": tests}


@router.get("/skills", response_model=DataResponse[dict])
async def get_skills_analysis(
    period: str = Query(default="30d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Get skills demand analysis from job listings."""
    start = _period_start(period)

    result = await db.execute(
        select(Job.skills_required, Job.skills_preferred).where(
            Job.user_id == current_user.id,
            Job.is_deleted == False,  # noqa: E712
            Job.created_at >= start,
        )
    )

    required_counts: dict[str, int] = {}
    preferred_counts: dict[str, int] = {}
    for row in result.all():
        for skill in (row[0] or []):
            s = skill.lower().strip()
            required_counts[s] = required_counts.get(s, 0) + 1
        for skill in (row[1] or []):
            s = skill.lower().strip()
            preferred_counts[s] = preferred_counts.get(s, 0) + 1

    top_required = sorted(required_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    top_preferred = sorted(preferred_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    return {"data": {
        "top_required_skills": [{"skill": s, "count": c} for s, c in top_required],
        "top_preferred_skills": [{"skill": s, "count": c} for s, c in top_preferred],
        "total_jobs_analyzed": sum(required_counts.values()) + sum(preferred_counts.values()),
    }}


@router.get("/timing", response_model=DataResponse[dict])
async def get_timing_analysis(
    period: str = Query(default="90d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Get application timing analysis."""
    start = _period_start(period)

    # Average time from application to response
    result = await db.execute(
        select(
            func.avg(
                func.extract("epoch", Application.updated_at) -
                func.extract("epoch", Application.created_at)
            )
        ).where(
            Application.user_id == current_user.id,
            Application.is_deleted == False,  # noqa: E712
            Application.status.in_(["screening", "interview", "offer", "rejected"]),
            Application.created_at >= start,
        )
    )
    avg_response_seconds = result.scalar() or 0

    # Jobs per day of week
    dow_result = await db.execute(
        select(
            func.extract("dow", Job.created_at).label("dow"),
            func.count(Job.id),
        ).where(
            Job.user_id == current_user.id,
            Job.is_deleted == False,  # noqa: E712
            Job.created_at >= start,
        ).group_by("dow")
    )
    by_day = {int(row[0]): row[1] for row in dow_result.all()}
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    jobs_by_day = [{
        "day": days[i], "count": by_day.get(i, 0)
    } for i in range(7)]

    return {"data": {
        "avg_response_time_days": round(avg_response_seconds / 86400, 1) if avg_response_seconds else 0,
        "jobs_by_day_of_week": jobs_by_day,
        "best_application_day": max(jobs_by_day, key=lambda x: x["count"])["day"] if any(d["count"] for d in jobs_by_day) else "N/A",
    }}


@router.post("/export")
async def export_analytics(
    body: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export analytics data as CSV/PDF."""
    from app.tasks.analytics_tasks import export_data

    result = export_data.delay(
        str(current_user.id), body.type, body.period, body.format,
    )
    return {"task_id": result.id}
