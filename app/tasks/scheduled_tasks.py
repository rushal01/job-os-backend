"""Celery Beat scheduled tasks for periodic job discovery, scoring, and cleanup."""

import asyncio
from datetime import UTC, datetime, timedelta

from loguru import logger

from app.tasks.celery_app import celery_app


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="scheduled.run_all_discoveries")
def run_all_discoveries():
    """Run job discovery for all users with active profiles and automation enabled."""
    async def _run():
        from sqlalchemy import select
        from app.db.session import async_session
        from app.models.profile import Profile
        from app.tasks.discovery_tasks import discover_jobs

        async with async_session() as db:
            # Find all active profiles with auto_discover enabled
            result = await db.execute(
                select(Profile).where(
                    Profile.is_active == True,
                    Profile.is_deleted == False,
                )
            )
            profiles = result.scalars().all()

            queued = 0
            for profile in profiles:
                auto_config = profile.automation_config or {}
                if not auto_config.get("auto_discover", True):
                    continue
                discover_jobs.delay(str(profile.user_id), str(profile.id))
                queued += 1

            logger.info(f"Scheduled discovery: queued {queued} profiles")
            return {"queued": queued}

    return _run_async(_run())


@celery_app.task(name="scheduled.auto_score_new_jobs")
def auto_score_new_jobs():
    """Score all new (unscored) jobs."""
    async def _run():
        from sqlalchemy import select
        from app.db.session import async_session
        from app.models.job import Job
        from app.tasks.scoring_tasks import score_job

        async with async_session() as db:
            result = await db.execute(
                select(Job).where(Job.status == "new", Job.score == None)
            )
            jobs = result.scalars().all()

            queued = 0
            for job in jobs:
                score_job.delay(str(job.user_id), str(job.id))
                queued += 1

            logger.info(f"Auto-score: queued {queued} unscored jobs")
            return {"queued": queued}

    return _run_async(_run())


@celery_app.task(name="scheduled.cleanup_old_notifications")
def cleanup_old_notifications():
    """Delete read notifications older than 30 days."""
    async def _run():
        from sqlalchemy import delete
        from app.db.session import async_session
        from app.models.notification import Notification

        cutoff = datetime.now(UTC) - timedelta(days=30)
        async with async_session() as db:
            result = await db.execute(
                delete(Notification).where(
                    Notification.read == True,
                    Notification.created_at < cutoff,
                )
            )
            await db.commit()
            deleted = result.rowcount
            logger.info(f"Cleanup: deleted {deleted} old read notifications")
            return {"deleted": deleted}

    return _run_async(_run())


@celery_app.task(name="scheduled.expire_stale_jobs")
def expire_stale_jobs():
    """Mark jobs older than 60 days as expired."""
    async def _run():
        from sqlalchemy import update
        from app.db.session import async_session
        from app.models.job import Job

        cutoff = datetime.now(UTC) - timedelta(days=60)
        async with async_session() as db:
            result = await db.execute(
                update(Job).where(
                    Job.status.in_(["new", "scored"]),
                    Job.created_at < cutoff,
                ).values(status="expired")
            )
            await db.commit()
            expired = result.rowcount
            logger.info(f"Expired {expired} stale jobs")
            return {"expired": expired}

    return _run_async(_run())
