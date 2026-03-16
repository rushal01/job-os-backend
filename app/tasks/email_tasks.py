"""Email tasks — Gmail inbox scanning for job-related status updates."""

from loguru import logger

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="email.scan_inbox")
def scan_inbox(self, user_id: str) -> dict:
    """Scan Gmail inbox for job-related emails.

    Detects:
    - Rejection emails -> update application status to 'rejected'
    - Interview invites -> create Interview record
    - Offer emails -> update application status to 'offer'

    Requires Gmail OAuth setup.
    """
    logger.info("Inbox scan requested for user {}", user_id)
    return {
        "emails_scanned": 0,
        "matches_found": 0,
        "message": "Email scanning requires Gmail OAuth setup. Configure in Settings > Email.",
    }


@celery_app.task(bind=True, name="email.send_outreach")
def send_email(self, user_id: str, message_id: str) -> dict:
    """Send an outreach email via Gmail API."""
    logger.info("Email send requested for user {}, message {}", user_id, message_id)
    return {
        "sent": False,
        "message": "Email sending requires SMTP configuration. Configure in Settings > Email.",
    }
