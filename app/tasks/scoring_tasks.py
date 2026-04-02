"""Scoring tasks — AI-powered job-profile match scoring."""

import asyncio
import uuid

from loguru import logger

from app.tasks.celery_app import celery_app


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="scoring.score_job",
                 autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def score_job(self, user_id: str, job_id: str) -> dict:
    """Score a single job against the user's active profile."""

    async def _score():
        from sqlalchemy import select

        from app.db.session import async_session
        from app.models.job import Job
        from app.models.profile import Profile
        from app.models.skill import Skill
        from app.services.scoring_service import score_job as do_score

        uid = uuid.UUID(user_id)
        jid = uuid.UUID(job_id)

        async with async_session() as db:
            # Load job
            result = await db.execute(select(Job).where(Job.id == jid, Job.user_id == uid))
            job = result.scalar_one_or_none()
            if not job:
                return {"error": "Job not found"}

            # Load active profile
            result = await db.execute(
                select(Profile).where(Profile.user_id == uid, Profile.is_active == True)  # noqa: E712
            )
            profile = result.scalar_one_or_none()
            if not profile:
                return {"error": "No active profile"}

            # Load skills
            result = await db.execute(select(Skill).where(Skill.user_id == uid))
            skills = list(result.scalars().all())

            # Score
            score_result = await do_score(db, job, profile, skills)

            # Update job
            job.score = score_result.score
            job.score_breakdown = score_result.score_breakdown
            job.confidence = score_result.confidence
            job.risk_score = score_result.risk_score
            job.decision = score_result.decision
            job.decision_reasoning = score_result.decision_reasoning
            job.skills_matched = score_result.skills_matched
            job.skills_missing = score_result.skills_missing
            job.status = "scored"

            await db.commit()
            logger.info(f"Scored job {job_id}: {score_result.score} ({score_result.decision})")
            return {
                "job_id": job_id,
                "score": score_result.score,
                "decision": score_result.decision,
            }

    return _run_async(_score())


@celery_app.task(bind=True, name="scoring.bulk_score_jobs",
                 autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def bulk_score_jobs(self, user_id: str, job_ids: list[str]) -> dict:
    """Score multiple jobs in batch. Updates progress as each job is scored."""

    async def _bulk():
        results = []
        total = len(job_ids)
        for i, jid in enumerate(job_ids):
            try:
                r = score_job(user_id, jid)
                results.append(r)
            except Exception as e:
                logger.error(f"Failed to score job {jid}: {e}")
                results.append({"job_id": jid, "error": str(e)})
            self.update_state(state="PROGRESS", meta={"progress_pct": (i + 1) / total * 100})
        return {"scored": len(results), "results": results}

    return _run_async(_bulk())
