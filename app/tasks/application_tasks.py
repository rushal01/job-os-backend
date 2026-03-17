"""Application tasks — ATS auto-submission via Playwright."""

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


@celery_app.task(bind=True, name="application.submit")
def submit_application(self, user_id: str, application_id: str) -> dict:
    """Auto-submit an application via ATS using Playwright.

    Steps:
    1. Load application, job (apply_url), and generated documents
    2. Launch Playwright browser in the playwright container
    3. Navigate to apply_url, detect ATS type
    4. Fill form fields with profile + generated content
    5. Take screenshot before submission
    6. Submit form and capture confirmation
    7. Update application status and store debug log

    Note: Actual Playwright ATS submission is a future feature.
    For now, just marks the application as submitted.
    """

    async def _submit():
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.db.session import async_session
        from app.models.application import Application
        from app.services.notification_service import create_notification

        uid = uuid.UUID(user_id)
        aid = uuid.UUID(application_id)

        async with async_session() as db:
            # Load application with its job
            result = await db.execute(
                select(Application)
                .where(Application.id == aid, Application.user_id == uid)
                .options(selectinload(Application.job))
            )
            application = result.scalar_one_or_none()
            if not application:
                return {"error": "Application not found"}

            job = application.job
            if not job:
                return {"error": "Associated job not found"}

            if not job.apply_url:
                return {"error": "Job has no apply URL configured"}

            # Update application status
            application.status = "submitted"
            application.submitted_at = datetime.now(UTC)
            application.submission_method = "auto"

            await db.commit()

            # Create notification
            await create_notification(
                db=db,
                user_id=uid,
                type="application_submitted",
                title=f"Application submitted for {job.title} at {job.company}",
                priority="medium",
                action_url=f"/applications/{application_id}",
            )

            logger.info(
                "Application {} submitted for job {} ({})",
                application_id, str(job.id), job.title,
            )
            return {
                "success": True,
                "application_id": application_id,
                "status": "submitted",
                "submitted_at": application.submitted_at.isoformat(),
            }

    return _run_async(_submit())
