"""Analytics schemas — API Contract Section 4.11.

Defines response models for funnel, sources, rejections, AI cost, and dashboard stats.
"""

from pydantic import BaseModel


class FunnelData(BaseModel):
    """Application funnel data — GET /analytics/funnel."""

    new: int = 0
    scored: int = 0
    content_ready: int = 0
    applied: int = 0
    interview: int = 0
    offer: int = 0
    rejected: int = 0


class SourceStats(BaseModel):
    """Per-source statistics — GET /analytics/sources."""

    source: str
    jobs_found: int = 0
    applications_sent: int = 0
    interviews: int = 0
    conversion_rate: float = 0.0


class RejectionStats(BaseModel):
    """Rejection analysis — GET /analytics/rejections."""

    total_rejections: int = 0
    by_stage: dict = {}
    common_reasons: list[str] = []


class AICostStats(BaseModel):
    """AI usage cost breakdown — GET /analytics/ai-cost."""

    total_cost: float = 0.0
    by_provider: dict = {}
    by_task: dict = {}
    period: str = ""


class DashboardStats(BaseModel):
    """Dashboard summary — GET /analytics/dashboard-stats."""

    active_jobs: int = 0
    pending_reviews: int = 0
    applications_this_week: int = 0
    interviews_scheduled: int = 0
    response_rate: float = 0.0


class WeeklyReport(BaseModel):
    """Weekly report — GET /analytics/weekly-report."""

    week: str = ""
    jobs_discovered: int = 0
    applications_sent: int = 0
    interviews: int = 0
    offers: int = 0
    highlights: list[str] = []


class ExportRequest(BaseModel):
    """POST /analytics/export request body."""

    type: str
    period: str
    format: str = "csv"
