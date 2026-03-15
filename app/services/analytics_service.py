"""Analytics service — funnel, sources, rejections, AI cost, dashboard stats.

Implements analytics queries per API Contract Section 4.11.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession


async def get_funnel(db: AsyncSession, user_id: uuid.UUID, period: str, profile_id: uuid.UUID | None) -> dict:
    """Compute application funnel data (new → scored → applied → interview → offer)."""
    raise NotImplementedError


async def get_sources(db: AsyncSession, user_id: uuid.UUID, period: str, profile_id: uuid.UUID | None) -> list[dict]:
    """Compute per-source statistics."""
    raise NotImplementedError


async def get_rejections(db: AsyncSession, user_id: uuid.UUID, period: str) -> dict:
    """Analyze rejections by stage and reason."""
    raise NotImplementedError


async def get_ai_cost(db: AsyncSession, user_id: uuid.UUID, period: str) -> dict:
    """Compute AI usage cost breakdown by provider and task."""
    raise NotImplementedError


async def get_dashboard_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Compute dashboard summary statistics."""
    raise NotImplementedError


async def get_weekly_report(db: AsyncSession, user_id: uuid.UUID, week: str | None) -> dict:
    """Generate weekly activity report."""
    raise NotImplementedError


async def export_analytics(db: AsyncSession, user_id: uuid.UUID, export_type: str, period: str, fmt: str) -> bytes:
    """Export analytics data as CSV or PDF. Returns file bytes."""
    raise NotImplementedError
