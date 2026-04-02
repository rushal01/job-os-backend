"""Market Intelligence API endpoints.

Referenced by file tree spec: app/api/v1/market.py
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse
from app.schemas.market import MarketInsight
from app.services import market_service

router = APIRouter(prefix="/market")


@router.get("/insights", response_model=DataResponse[list[MarketInsight]])
async def get_market_insights(
    role: str | None = None,
    location: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[MarketInsight]]:
    """Get market intelligence for a role/location."""
    insights = await market_service.get_market_insights(db, role, location)
    return DataResponse(data=[MarketInsight(**i) for i in insights])


@router.get("/salary", response_model=DataResponse[dict])
async def get_salary_data(
    role: str = Query(...),
    location: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Get salary data for a role/location."""
    data = await market_service.get_salary_data(db, role, location)
    return DataResponse(data=data)


@router.get("/trends", response_model=DataResponse[dict])
async def get_market_trends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Get job market trends."""
    data = await market_service.get_market_trends(db)
    return DataResponse(data=data)
