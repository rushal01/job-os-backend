"""Market intelligence tasks — salary benchmarking and trend analysis."""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="market.compute_insights")
def compute_market_insights(self, role: str, location: str | None = None) -> dict:
    """Compute market intelligence for a role/location.

    Aggregates data from job postings to compute:
    - Average salary ranges
    - Demand score (based on posting volume)
    - Top required skills
    - Top hiring companies
    - Market trend (growing, stable, declining)
    """
    raise NotImplementedError
