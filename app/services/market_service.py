"""Market intelligence service — salary data, trends, and skill demand analysis."""

from sqlalchemy.ext.asyncio import AsyncSession


async def get_market_insights(db: AsyncSession, role: str | None, location: str | None) -> list[dict]:
    """Get market intelligence for a role/location combination."""
    raise NotImplementedError


async def get_salary_data(db: AsyncSession, role: str, location: str | None) -> dict:
    """Get salary benchmarks for a role/location."""
    raise NotImplementedError


async def get_market_trends(db: AsyncSession) -> dict:
    """Get overall job market trends."""
    raise NotImplementedError
