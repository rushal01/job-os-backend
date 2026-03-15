"""Analytics API endpoints — API Contract Section 4.11.

7 endpoints: funnel, sources, rejections, ai-cost, dashboard-stats, weekly-report, export.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    AICostStats,
    DashboardStats,
    ExportRequest,
    FunnelData,
    RejectionStats,
    SourceStats,
    WeeklyReport,
)
from app.schemas.common import DataResponse

router = APIRouter(prefix="/analytics")


@router.get("/funnel", response_model=DataResponse[FunnelData])
async def get_funnel(
    period: str = Query(default="30d"),
    profile_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[FunnelData]:
    """Get application funnel data."""
    raise NotImplementedError


@router.get("/sources", response_model=DataResponse[list[SourceStats]])
async def get_sources(
    period: str = Query(default="30d"),
    profile_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[SourceStats]]:
    """Get per-source statistics."""
    raise NotImplementedError


@router.get("/rejections", response_model=DataResponse[RejectionStats])
async def get_rejections(
    period: str = Query(default="30d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[RejectionStats]:
    """Get rejection analysis."""
    raise NotImplementedError


@router.get("/ai-cost", response_model=DataResponse[AICostStats])
async def get_ai_cost(
    period: str = Query(default="30d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AICostStats]:
    """Get AI usage cost breakdown."""
    raise NotImplementedError


@router.get("/dashboard-stats", response_model=DataResponse[DashboardStats])
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[DashboardStats]:
    """Get dashboard summary statistics."""
    raise NotImplementedError


@router.get("/weekly-report", response_model=DataResponse[WeeklyReport])
async def get_weekly_report(
    week: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[WeeklyReport]:
    """Get weekly report."""
    raise NotImplementedError


@router.post("/export")
async def export_analytics(
    body: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export analytics data as CSV/PDF."""
    raise NotImplementedError
