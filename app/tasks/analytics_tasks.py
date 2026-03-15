"""Analytics tasks — weekly report generation and data aggregation."""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="analytics.generate_weekly_report")
def generate_weekly_report(self, user_id: str) -> dict:
    """Generate and store a weekly activity report for a user."""
    raise NotImplementedError


@celery_app.task(bind=True, name="analytics.export_data")
def export_data(self, user_id: str, export_type: str, period: str, fmt: str) -> dict:
    """Export analytics data as CSV or PDF. Stores result in R2."""
    raise NotImplementedError
