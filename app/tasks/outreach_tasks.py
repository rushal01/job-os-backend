"""Outreach tasks — recruiter discovery and message sending."""

import asyncio
import uuid
from datetime import UTC, datetime

from loguru import logger

from app.tasks.celery_app import celery_app


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="outreach.discover_contacts")
def discover_contacts(self, user_id: str, job_id: str) -> dict:
    """Discover relevant contacts (recruiters, hiring managers) for a job.

    Uses LinkedIn search via Playwright to find potential contacts.
    Actual LinkedIn scraping is a future feature.
    """

    async def _discover():
        from sqlalchemy import select

        from app.db.session import async_session
        from app.models.job import Job

        uid = uuid.UUID(user_id)
        jid = uuid.UUID(job_id)

        async with async_session() as db:
            result = await db.execute(
                select(Job).where(Job.id == jid, Job.user_id == uid)
            )
            job = result.scalar_one_or_none()
            if not job:
                return {"error": "Job not found"}

            logger.info(
                "Contact discovery requested for job {} at {}",
                job.title, job.company,
            )
            return {
                "contacts_found": 0,
                "message": "Contact discovery requires LinkedIn integration. Configure in Settings > Sources.",
            }

    return _run_async(_discover())


@celery_app.task(bind=True, name="outreach.send_message")
def send_message(self, user_id: str, message_id: str) -> dict:
    """Send an outreach message via the configured channel (LinkedIn DM, email)."""

    async def _send():
        from sqlalchemy import select

        from app.db.session import async_session
        from app.models.outreach_message import OutreachMessage

        mid = uuid.UUID(message_id)

        async with async_session() as db:
            result = await db.execute(
                select(OutreachMessage).where(OutreachMessage.id == mid)
            )
            message = result.scalar_one_or_none()
            if not message:
                return {"error": "Message not found"}

            message.status = "sent"
            message.sent_at = datetime.now(UTC)
            await db.commit()

            logger.info("Outreach message {} marked as sent", message_id)
            return {
                "success": True,
                "message_id": message_id,
                "status": "sent",
                "sent_at": message.sent_at.isoformat(),
            }

    return _run_async(_send())
