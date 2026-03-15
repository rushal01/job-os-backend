"""Application tasks — ATS auto-submission via Playwright."""

from app.tasks.celery_app import celery_app


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
    """
    raise NotImplementedError
