"""Discovery tasks — job discovery with normalization and deduplication."""

import asyncio
import hashlib
import uuid
from datetime import UTC, datetime

from loguru import logger

from app.tasks.celery_app import celery_app


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def compute_dedup_hash(company: str, title: str, location: str | None) -> str:
    """Normalize (lowercase, strip) + SHA256 hash for deduplication."""
    normalized = f"{company.lower().strip()}|{title.lower().strip()}|{(location or '').lower().strip()}"
    return hashlib.sha256(normalized.encode()).hexdigest()


def normalize_raw_job(raw_data: dict) -> dict:
    """Extract and normalize fields from raw scraped job data."""
    return {
        "title": (raw_data.get("title") or "").strip(),
        "company": (raw_data.get("company") or "").strip(),
        "location": (raw_data.get("location") or "").strip() or None,
        "location_type": raw_data.get("location_type"),
        "seniority": raw_data.get("seniority"),
        "employment_type": raw_data.get("employment_type"),
        "description": raw_data.get("description"),
        "apply_url": raw_data.get("apply_url"),
        "ats_type": raw_data.get("ats_type"),
        "posted_date": raw_data.get("posted_date"),
        "salary_min": raw_data.get("salary_min"),
        "salary_max": raw_data.get("salary_max"),
        "salary_currency": raw_data.get("salary_currency"),
        "skills_required": raw_data.get("skills_required", []),
        "skills_preferred": raw_data.get("skills_preferred", []),
    }


@celery_app.task(bind=True, name="discovery.discover_jobs",
                 autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def discover_jobs(self, user_id: str, profile_id: str) -> dict:
    """Discover new jobs from configured sources for a profile.

    1. Load profile's discovery_config
    2. For each source: scrape (mock for now)
    3. Normalize raw job data → RawJob records
    4. Deduplicate via dedup_hash
    5. Create Job records for new unique postings
    6. Create JobSource junction rows
    """

    async def _discover():
        from sqlalchemy import select

        from app.db.session import async_session
        from app.models.job import Job
        from app.models.job_source import JobSource
        from app.models.profile import Profile
        from app.models.raw_job import RawJob

        uid = uuid.UUID(user_id)
        pid = uuid.UUID(profile_id)

        async with async_session() as db:
            # Load profile
            result = await db.execute(select(Profile).where(Profile.id == pid, Profile.user_id == uid))
            profile = result.scalar_one_or_none()
            if not profile:
                return {"error": "Profile not found"}

            config = profile.discovery_config or {}
            sources = config.get("sources_enabled", ["mock"])
            keywords = config.get("keywords", [profile.target_role])

            # Mock scraping — in Sprint 4, this will use Playwright
            raw_results = _mock_scrape(sources, keywords)

            created_jobs = 0
            total_raw = len(raw_results)

            for i, raw in enumerate(raw_results):
                normalized = normalize_raw_job(raw)
                title = normalized["title"]
                company = normalized["company"]
                if not title or not company:
                    continue

                dedup = compute_dedup_hash(company, title, normalized.get("location"))

                # Check existing raw_job
                existing = await db.execute(
                    select(RawJob).where(RawJob.dedup_hash == dedup)
                )
                existing_raw = existing.scalar_one_or_none()

                if existing_raw:
                    # Already seen — just add source link if new source
                    raw_job = existing_raw
                else:
                    # New raw job
                    raw_job = RawJob(
                        source=raw.get("source", "mock"),
                        source_url=raw.get("source_url"),
                        dedup_hash=dedup,
                        raw_data=raw,
                        normalized_title=title,
                        normalized_company=company,
                        normalized_location=normalized.get("location"),
                    )
                    db.add(raw_job)
                    await db.flush()

                    # Create Job record
                    job = Job(
                        user_id=uid,
                        profile_id=pid,
                        title=title,
                        company=company,
                        location=normalized.get("location"),
                        location_type=normalized.get("location_type"),
                        seniority=normalized.get("seniority"),
                        employment_type=normalized.get("employment_type"),
                        description=normalized.get("description"),
                        apply_url=normalized.get("apply_url"),
                        ats_type=normalized.get("ats_type"),
                        posted_date=normalized.get("posted_date"),
                        salary_min=normalized.get("salary_min"),
                        salary_max=normalized.get("salary_max"),
                        salary_currency=normalized.get("salary_currency"),
                        skills_required=normalized.get("skills_required", []),
                        skills_preferred=normalized.get("skills_preferred", []),
                        status="new",
                    )
                    db.add(job)
                    await db.flush()

                    # Junction row
                    js = JobSource(
                        job_id=job.id,
                        raw_job_id=raw_job.id,
                        source=raw.get("source", "mock"),
                        scraped_at=datetime.now(UTC),
                    )
                    db.add(js)
                    created_jobs += 1

                self.update_state(
                    state="PROGRESS",
                    meta={"progress_pct": (i + 1) / max(total_raw, 1) * 100},
                )

            await db.commit()
            logger.info(f"Discovery complete: {created_jobs} new jobs from {total_raw} raw results")
            return {"created_jobs": created_jobs, "total_raw": total_raw}

    return _run_async(_discover())


def _mock_scrape(sources: list[str], keywords: list[str]) -> list[dict]:
    """Mock scraping — returns sample data. Real Playwright in Sprint 4."""
    results = []
    for kw in keywords[:1]:  # limit for mock
        results.append({
            "source": "mock_linkedin",
            "title": f"Senior {kw}",
            "company": "TechCorp Inc",
            "location": "San Francisco, CA",
            "location_type": "hybrid",
            "seniority": "Senior",
            "employment_type": "Full-time",
            "description": f"Looking for a skilled {kw} to join our team.",
            "apply_url": "https://example.com/apply/1",
            "posted_date": datetime.now(UTC).isoformat(),
            "skills_required": ["python", "sql", "docker"],
            "skills_preferred": ["kubernetes", "aws"],
        })
    return results
