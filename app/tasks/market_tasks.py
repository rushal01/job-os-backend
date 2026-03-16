"""Market intelligence tasks — salary benchmarking and trend analysis."""

import asyncio
import json
import uuid
from collections import defaultdict

from loguru import logger

from app.tasks.celery_app import celery_app


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="market.compute_insights")
def compute_market_insights(self, user_id: str) -> dict:
    """Compute market intelligence for a user based on their tracked jobs.

    Aggregates data from job postings to compute:
    - Skill demand counts
    - Salary ranges by role/title
    """

    async def _compute():
        import redis.asyncio as aioredis
        from sqlalchemy import select

        from app.config import settings
        from app.db.session import async_session
        from app.models.job import Job

        uid = uuid.UUID(user_id)

        async with async_session() as db:
            result = await db.execute(
                select(Job).where(Job.user_id == uid)
            )
            jobs = list(result.scalars().all())

            if not jobs:
                insights = {
                    "user_id": user_id,
                    "total_jobs_analyzed": 0,
                    "skill_demand": {},
                    "salary_ranges": {},
                    "message": "No jobs found. Discover jobs to generate market insights.",
                }
            else:
                # Aggregate skill demand
                skill_counts: dict[str, int] = defaultdict(int)
                for job in jobs:
                    for skill in (job.skills_required or []):
                        skill_counts[skill.lower()] += 1
                    for skill in (job.skills_preferred or []):
                        skill_counts[skill.lower()] += 1

                # Sort by demand (descending)
                skill_demand = dict(
                    sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
                )

                # Aggregate salary ranges by title
                salary_by_title: dict[str, dict] = defaultdict(
                    lambda: {"min_values": [], "max_values": [], "count": 0}
                )
                for job in jobs:
                    if job.salary_min is not None or job.salary_max is not None:
                        title_key = job.title.strip()
                        entry = salary_by_title[title_key]
                        entry["count"] += 1
                        if job.salary_min is not None:
                            entry["min_values"].append(job.salary_min)
                        if job.salary_max is not None:
                            entry["max_values"].append(job.salary_max)

                salary_ranges = {}
                for title, data in salary_by_title.items():
                    salary_ranges[title] = {
                        "count": data["count"],
                        "avg_min": (
                            round(sum(data["min_values"]) / len(data["min_values"]))
                            if data["min_values"] else None
                        ),
                        "avg_max": (
                            round(sum(data["max_values"]) / len(data["max_values"]))
                            if data["max_values"] else None
                        ),
                        "lowest": min(data["min_values"]) if data["min_values"] else None,
                        "highest": max(data["max_values"]) if data["max_values"] else None,
                    }

                insights = {
                    "user_id": user_id,
                    "total_jobs_analyzed": len(jobs),
                    "skill_demand": skill_demand,
                    "salary_ranges": salary_ranges,
                }

            # Cache in Redis
            try:
                r = aioredis.from_url(settings.REDIS_URL)
                cache_key = f"market_insights:{user_id}"
                await r.set(cache_key, json.dumps(insights), ex=3600)  # 1 hour TTL
                await r.aclose()
            except Exception as e:
                logger.warning("Failed to cache market insights in Redis: {}", e)

            logger.info(
                "Market insights computed for user {}: {} jobs analyzed",
                user_id, len(jobs),
            )
            return insights

    return _run_async(_compute())
