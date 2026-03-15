"""Content generation tasks — async resume, cover letter, answer generation."""

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


@celery_app.task(bind=True, name="content.generate_resume",
                 autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_resume(self, user_id: str, job_id: str, profile_id: str,
                    instructions: str | None = None) -> dict:
    """Generate a tailored resume using AI."""

    async def _gen():
        from app.db.session import async_session
        from app.services.content_service import generate_resume_impl

        async with async_session() as db:
            result = await generate_resume_impl(
                db, uuid.UUID(user_id), uuid.UUID(job_id),
                uuid.UUID(profile_id), instructions,
            )
            await db.commit()
            return result

    return _run_async(_gen())


@celery_app.task(bind=True, name="content.generate_cover_letter",
                 autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_cover_letter(self, user_id: str, job_id: str, profile_id: str) -> dict:
    """Generate a cover letter using AI."""

    async def _gen():
        from app.db.session import async_session
        from app.services.content_service import generate_cover_letter_impl

        async with async_session() as db:
            result = await generate_cover_letter_impl(
                db, uuid.UUID(user_id), uuid.UUID(job_id), uuid.UUID(profile_id),
            )
            await db.commit()
            return result

    return _run_async(_gen())


@celery_app.task(bind=True, name="content.generate_answers",
                 autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_answers(self, user_id: str, job_id: str, questions: list[str]) -> dict:
    """Generate answers to application questions using AI."""

    async def _gen():
        from app.db.session import async_session
        from app.services.content_service import generate_answers_impl

        async with async_session() as db:
            result = await generate_answers_impl(
                db, uuid.UUID(user_id), uuid.UUID(job_id), questions,
            )
            await db.commit()
            return result

    return _run_async(_gen())


@celery_app.task(bind=True, name="content.regenerate_document",
                 autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def regenerate_document(self, user_id: str, document_id: str, instructions: str) -> dict:
    """Regenerate a document with new instructions."""

    async def _gen():
        from app.db.session import async_session
        from app.services.content_service import regenerate_document_impl

        async with async_session() as db:
            result = await regenerate_document_impl(
                db, uuid.UUID(user_id), uuid.UUID(document_id), instructions,
            )
            await db.commit()
            return result

    return _run_async(_gen())
