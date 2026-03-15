"""Market intelligence schemas.

Referenced by file tree spec: app/schemas/market.py
"""

from pydantic import BaseModel


class MarketInsight(BaseModel):
    """Market intelligence data for a role/location."""

    role: str
    location: str | None = None
    avg_salary: float | None = None
    demand_score: float | None = None
    top_skills: list[str] = []
    top_companies: list[str] = []
    trend: str | None = None  # growing, stable, declining
