"""Market intelligence service — salary data, trends, and skill demand analysis."""

from collections import Counter
from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job


async def get_market_insights(
    db: AsyncSession, role: str | None, location: str | None
) -> list[dict]:
    """Get market intelligence for a role/location combination."""
    query = select(Job).where(Job.is_deleted == False)  # noqa: E712

    if role:
        query = query.where(Job.title.ilike(f"%{role}%"))
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))

    result = await db.execute(query)
    jobs = list(result.scalars().all())

    if not jobs:
        return []

    # Count jobs by company (top companies)
    company_counts: Counter[str] = Counter()
    all_skills: Counter[str] = Counter()
    salary_values: list[float] = []

    for job in jobs:
        company_counts[job.company] += 1

        # Extract skills from skills_required
        if job.skills_required:
            for skill in job.skills_required:
                if isinstance(skill, str):
                    all_skills[skill] += 1

        # Average salary
        if job.salary_min is not None and job.salary_max is not None:
            salary_values.append((job.salary_min + job.salary_max) / 2)
        elif job.salary_min is not None:
            salary_values.append(float(job.salary_min))
        elif job.salary_max is not None:
            salary_values.append(float(job.salary_max))

    top_companies = [c for c, _ in company_counts.most_common(10)]
    top_skills = [s for s, _ in all_skills.most_common(10)]
    avg_salary = sum(salary_values) / len(salary_values) if salary_values else None

    # Determine demand trend based on job count
    total_jobs = len(jobs)
    if total_jobs >= 50:
        trend = "growing"
    elif total_jobs >= 10:
        trend = "stable"
    else:
        trend = "declining"

    insight = {
        "role": role or "all",
        "location": location,
        "avg_salary": round(avg_salary, 2) if avg_salary else None,
        "demand_score": min(total_jobs / 10.0, 10.0),
        "top_skills": top_skills,
        "top_companies": top_companies,
        "trend": trend,
    }

    logger.info(
        "Market insights: role={}, location={}, jobs_found={}",
        role, location, total_jobs,
    )
    return [insight]


async def get_salary_data(
    db: AsyncSession, role: str, location: str | None
) -> dict:
    """Get salary benchmarks for a role/location."""
    query = select(Job).where(
        Job.is_deleted == False,  # noqa: E712
        Job.title.ilike(f"%{role}%"),
        Job.salary_min.isnot(None),
        Job.salary_max.isnot(None),
    )

    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))

    result = await db.execute(query)
    jobs = list(result.scalars().all())

    if not jobs:
        return {
            "role": role,
            "location": location,
            "min_salary": None,
            "max_salary": None,
            "avg_salary": None,
            "median_salary": None,
            "sample_size": 0,
        }

    # Collect salary midpoints for median calculation
    salary_mins: list[int] = []
    salary_maxes: list[int] = []
    salary_midpoints: list[float] = []

    for job in jobs:
        salary_mins.append(job.salary_min)
        salary_maxes.append(job.salary_max)
        salary_midpoints.append((job.salary_min + job.salary_max) / 2)

    salary_midpoints.sort()
    n = len(salary_midpoints)
    if n % 2 == 1:
        median_salary = salary_midpoints[n // 2]
    else:
        median_salary = (salary_midpoints[n // 2 - 1] + salary_midpoints[n // 2]) / 2

    return {
        "role": role,
        "location": location,
        "min_salary": min(salary_mins),
        "max_salary": max(salary_maxes),
        "avg_salary": round(sum(salary_midpoints) / n, 2),
        "median_salary": round(median_salary, 2),
        "sample_size": n,
    }


async def get_market_trends(db: AsyncSession) -> dict:
    """Get overall job market trends."""
    now = datetime.now(timezone.utc)
    twelve_weeks_ago = now - timedelta(weeks=12)
    eight_weeks_ago = now - timedelta(weeks=8)
    four_weeks_ago = now - timedelta(weeks=4)

    # Jobs posted per week (last 12 weeks)
    weekly_query = (
        select(
            func.date_trunc("week", Job.created_at).label("week"),
            func.count(Job.id).label("count"),
        )
        .where(
            Job.is_deleted == False,  # noqa: E712
            Job.created_at >= twelve_weeks_ago,
        )
        .group_by(func.date_trunc("week", Job.created_at))
        .order_by(func.date_trunc("week", Job.created_at))
    )
    weekly_result = await db.execute(weekly_query)
    jobs_per_week = [
        {"week": str(row.week), "count": row.count}
        for row in weekly_result
    ]

    # Top growing skills: compare last 4 weeks vs prior 4 weeks
    recent_query = select(Job.skills_required).where(
        Job.is_deleted == False,  # noqa: E712
        Job.created_at >= four_weeks_ago,
    )
    prior_query = select(Job.skills_required).where(
        Job.is_deleted == False,  # noqa: E712
        Job.created_at >= eight_weeks_ago,
        Job.created_at < four_weeks_ago,
    )

    recent_result = await db.execute(recent_query)
    prior_result = await db.execute(prior_query)

    recent_skills: Counter[str] = Counter()
    prior_skills: Counter[str] = Counter()

    for (skills_list,) in recent_result:
        if skills_list:
            for skill in skills_list:
                if isinstance(skill, str):
                    recent_skills[skill] += 1

    for (skills_list,) in prior_result:
        if skills_list:
            for skill in skills_list:
                if isinstance(skill, str):
                    prior_skills[skill] += 1

    # Growing skills = skills that increased most
    growing_skills: list[dict] = []
    all_skill_names = set(recent_skills.keys()) | set(prior_skills.keys())
    for skill in all_skill_names:
        recent_count = recent_skills.get(skill, 0)
        prior_count = prior_skills.get(skill, 0)
        growth = recent_count - prior_count
        if growth > 0:
            growing_skills.append({"skill": skill, "growth": growth})

    growing_skills.sort(key=lambda x: x["growth"], reverse=True)
    top_growing_skills = growing_skills[:10]

    # Most active companies
    company_query = (
        select(Job.company, func.count(Job.id).label("count"))
        .where(
            Job.is_deleted == False,  # noqa: E712
            Job.created_at >= four_weeks_ago,
        )
        .group_by(Job.company)
        .order_by(func.count(Job.id).desc())
        .limit(10)
    )
    company_result = await db.execute(company_query)
    most_active_companies = [
        {"company": row.company, "count": row.count}
        for row in company_result
    ]

    # Remote vs hybrid vs onsite percentages
    total_query = select(func.count(Job.id)).where(
        Job.is_deleted == False,  # noqa: E712
        Job.created_at >= four_weeks_ago,
    )
    total_result = await db.execute(total_query)
    total_jobs = total_result.scalar() or 0

    if total_jobs > 0:
        location_type_query = (
            select(
                Job.location_type,
                func.count(Job.id).label("count"),
            )
            .where(
                Job.is_deleted == False,  # noqa: E712
                Job.created_at >= four_weeks_ago,
            )
            .group_by(Job.location_type)
        )
        lt_result = await db.execute(location_type_query)
        lt_counts = {row.location_type: row.count for row in lt_result}

        remote_pct = round(lt_counts.get("remote", 0) / total_jobs * 100, 1)
        hybrid_pct = round(lt_counts.get("hybrid", 0) / total_jobs * 100, 1)
        onsite_pct = round(lt_counts.get("onsite", 0) / total_jobs * 100, 1)
    else:
        remote_pct = 0.0
        hybrid_pct = 0.0
        onsite_pct = 0.0

    logger.info("Generated market trends")
    return {
        "jobs_per_week": jobs_per_week,
        "top_growing_skills": top_growing_skills,
        "most_active_companies": most_active_companies,
        "location_type_breakdown": {
            "remote_pct": remote_pct,
            "hybrid_pct": hybrid_pct,
            "onsite_pct": onsite_pct,
        },
    }
