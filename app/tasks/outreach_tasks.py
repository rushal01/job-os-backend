"""Outreach tasks — recruiter discovery and message sending."""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="outreach.discover_contacts")
def discover_contacts(self, user_id: str, job_id: str) -> dict:
    """Discover relevant contacts (recruiters, hiring managers) for a job.

    Uses LinkedIn search via Playwright to find potential contacts.
    """
    raise NotImplementedError


@celery_app.task(bind=True, name="outreach.send_message")
def send_message(self, user_id: str, message_id: str) -> dict:
    """Send an outreach message via the configured channel (LinkedIn DM, email)."""
    raise NotImplementedError
