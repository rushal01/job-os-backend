"""Analytics tasks — weekly report generation and data aggregation."""

import asyncio
import csv
import io
import uuid
from datetime import UTC, datetime, timedelta

from loguru import logger

from app.tasks.celery_app import celery_app


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="analytics.generate_weekly_report")
def generate_weekly_report(self, user_id: str) -> dict:
    """Generate and store a weekly activity report for a user."""

    async def _generate():
        from sqlalchemy import select

        from app.db.session import async_session
        from app.models.application import Application
        from app.models.interview import Interview
        from app.models.job import Job
        from app.services.notification_service import create_notification

        uid = uuid.UUID(user_id)
        now = datetime.now(UTC)
        # Start of the current week (Monday)
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

        async with async_session() as db:
            # 1. Jobs created this week
            result = await db.execute(
                select(Job).where(
                    Job.user_id == uid,
                    Job.created_at >= start_of_week,
                )
            )
            jobs = list(result.scalars().all())
            jobs_count = len(jobs)

            # Count jobs by status
            jobs_by_status: dict[str, int] = {}
            for job in jobs:
                jobs_by_status[job.status] = jobs_by_status.get(job.status, 0) + 1

            # 2. Applications submitted this week
            result = await db.execute(
                select(Application).where(
                    Application.user_id == uid,
                    Application.created_at >= start_of_week,
                )
            )
            applications = list(result.scalars().all())
            applications_count = len(applications)

            # Count applications by status
            apps_by_status: dict[str, int] = {}
            for app in applications:
                apps_by_status[app.status] = apps_by_status.get(app.status, 0) + 1

            # 3. Interviews scheduled this week
            result = await db.execute(
                select(Interview).where(
                    Interview.user_id == uid,
                    Interview.created_at >= start_of_week,
                )
            )
            interviews = list(result.scalars().all())
            interviews_count = len(interviews)

            # Build summary
            stats = {
                "week_start": start_of_week.isoformat(),
                "week_end": now.isoformat(),
                "jobs_discovered": jobs_count,
                "jobs_by_status": jobs_by_status,
                "applications_submitted": applications_count,
                "applications_by_status": apps_by_status,
                "interviews_scheduled": interviews_count,
            }

            # 4. Create notification with summary
            summary_lines = [
                f"Jobs discovered: {jobs_count}",
                f"Applications submitted: {applications_count}",
                f"Interviews scheduled: {interviews_count}",
            ]
            summary_body = "\n".join(summary_lines)

            await create_notification(
                db=db,
                user_id=uid,
                type="weekly_report",
                title="Your Weekly Job Search Report",
                body=summary_body,
                priority="medium",
                extra_data=stats,
            )

            logger.info(
                "Weekly report generated for user {}: {} jobs, {} apps, {} interviews",
                user_id, jobs_count, applications_count, interviews_count,
            )
            return stats

    return _run_async(_generate())


@celery_app.task(bind=True, name="analytics.export_data")
def export_data(self, user_id: str, export_type: str, period: str, fmt: str) -> dict:
    """Export analytics data as CSV or PDF. Stores result in R2."""

    async def _export():
        from sqlalchemy import select

        from app.db.session import async_session
        from app.models.application import Application
        from app.models.job import Job

        uid = uuid.UUID(user_id)
        now = datetime.now(UTC)

        # Determine period filter
        period_map = {
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
        }
        since = None
        if period in period_map:
            since = now - period_map[period]

        async with async_session() as db:
            output = io.StringIO()
            writer = csv.writer(output)
            row_count = 0

            if export_type == "jobs":
                query = select(Job).where(Job.user_id == uid)
                if since:
                    query = query.where(Job.created_at >= since)
                query = query.order_by(Job.created_at.desc())
                result = await db.execute(query)
                jobs = list(result.scalars().all())

                writer.writerow([
                    "id", "title", "company", "location", "status",
                    "score", "salary_min", "salary_max", "created_at",
                ])
                for job in jobs:
                    writer.writerow([
                        str(job.id), job.title, job.company, job.location or "",
                        job.status, job.score or "", job.salary_min or "",
                        job.salary_max or "", job.created_at.isoformat() if job.created_at else "",
                    ])
                    row_count += 1

            elif export_type == "applications":
                query = select(Application).where(Application.user_id == uid)
                if since:
                    query = query.where(Application.created_at >= since)
                query = query.order_by(Application.created_at.desc())
                result = await db.execute(query)
                applications = list(result.scalars().all())

                writer.writerow([
                    "id", "job_id", "status", "submission_method",
                    "submitted_at", "created_at",
                ])
                for app in applications:
                    writer.writerow([
                        str(app.id), str(app.job_id), app.status,
                        app.submission_method or "",
                        app.submitted_at.isoformat() if app.submitted_at else "",
                        app.created_at.isoformat() if app.created_at else "",
                    ])
                    row_count += 1

            elif export_type == "analytics":
                # Aggregate analytics: jobs by status, apps by status
                job_query = select(Job).where(Job.user_id == uid)
                if since:
                    job_query = job_query.where(Job.created_at >= since)
                result = await db.execute(job_query)
                jobs = list(result.scalars().all())

                app_query = select(Application).where(Application.user_id == uid)
                if since:
                    app_query = app_query.where(Application.created_at >= since)
                result = await db.execute(app_query)
                applications = list(result.scalars().all())

                writer.writerow(["metric", "value"])
                writer.writerow(["total_jobs", len(jobs)])
                writer.writerow(["total_applications", len(applications)])
                row_count += 2

                # Jobs by status
                jobs_by_status: dict[str, int] = {}
                for job in jobs:
                    jobs_by_status[job.status] = jobs_by_status.get(job.status, 0) + 1
                for status, count in sorted(jobs_by_status.items()):
                    writer.writerow([f"jobs_{status}", count])
                    row_count += 1

                # Applications by status
                apps_by_status: dict[str, int] = {}
                for app in applications:
                    apps_by_status[app.status] = apps_by_status.get(app.status, 0) + 1
                for status, count in sorted(apps_by_status.items()):
                    writer.writerow([f"applications_{status}", count])
                    row_count += 1

            csv_data = output.getvalue()
            logger.info(
                "Exported {} data for user {}: {} rows",
                export_type, user_id, row_count,
            )
            return {"csv_data": csv_data, "row_count": row_count}

    return _run_async(_export())
