"""Email tasks — Gmail inbox scanning for job-related status updates."""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="email.scan_inbox")
def scan_inbox(self, user_id: str) -> dict:
    """Scan Gmail inbox for job-related emails.

    Detects:
    - Rejection emails → update application status to 'rejected'
    - Interview invites → create Interview record
    - Offer emails → update application status to 'offer'
    """
    raise NotImplementedError


@celery_app.task(bind=True, name="email.send_outreach")
def send_email(self, user_id: str, message_id: str) -> dict:
    """Send an outreach email via Gmail API."""
    raise NotImplementedError
