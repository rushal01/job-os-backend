"""Content generation service — AI-powered resume, cover letter, and answer generation.

Implements generate_resume_impl, generate_cover_letter_impl, generate_answers_impl,
regenerate_document_impl with QA verification and quality scoring.

Also provides top-level task-enqueueing functions (generate_resume, etc.) that
create a Task record and dispatch to Celery.
"""

import json
import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.models.document import Document
from app.models.job import Job
from app.models.profile import Profile
from app.models.review_queue import ReviewQueue
from app.models.task import Task

# ---------------------------------------------------------------------------
# Task-enqueueing helpers (called from routes)
# ---------------------------------------------------------------------------

async def generate_resume(
    db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID,
    profile_id: uuid.UUID, instructions: str | None = None,
) -> str:
    """Enqueue a resume generation task. Returns task_id."""
    task = Task(user_id=user_id, task_name="generate_resume", status="pending", progress_pct=0.0)
    db.add(task)
    await db.flush()
    await db.refresh(task)

    from app.tasks.content_tasks import generate_resume as celery_task
    result = celery_task.delay(str(user_id), str(job_id), str(profile_id), instructions)
    task.celery_task_id = result.id
    await db.flush()
    return str(task.id)


async def generate_cover_letter(
    db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID, profile_id: uuid.UUID,
) -> str:
    """Enqueue a cover letter generation task. Returns task_id."""
    task = Task(user_id=user_id, task_name="generate_cover_letter", status="pending", progress_pct=0.0)
    db.add(task)
    await db.flush()
    await db.refresh(task)

    from app.tasks.content_tasks import generate_cover_letter as celery_task
    result = celery_task.delay(str(user_id), str(job_id), str(profile_id))
    task.celery_task_id = result.id
    await db.flush()
    return str(task.id)


async def generate_answers(
    db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID, questions: list[str],
) -> str:
    """Enqueue an answer generation task. Returns task_id."""
    task = Task(user_id=user_id, task_name="generate_answers", status="pending", progress_pct=0.0)
    db.add(task)
    await db.flush()
    await db.refresh(task)

    from app.tasks.content_tasks import generate_answers as celery_task
    result = celery_task.delay(str(user_id), str(job_id), questions)
    task.celery_task_id = result.id
    await db.flush()
    return str(task.id)


async def regenerate_document(
    db: AsyncSession, user_id: uuid.UUID, document_id: uuid.UUID, instructions: str,
) -> str:
    """Enqueue a document regeneration task. Returns task_id."""
    task = Task(user_id=user_id, task_name="regenerate_document", status="pending", progress_pct=0.0)
    db.add(task)
    await db.flush()
    await db.refresh(task)

    from app.tasks.content_tasks import regenerate_document as celery_task
    result = celery_task.delay(str(user_id), str(document_id), instructions)
    task.celery_task_id = result.id
    await db.flush()
    return str(task.id)


# ---------------------------------------------------------------------------
# Quality scoring
# ---------------------------------------------------------------------------

def calculate_quality_score(content: str, doc_type: str) -> tuple[int, dict]:
    """Calculate quality score (1-100) with breakdown.

    Checks: length, structure, completeness, relevance.
    Returns (score, breakdown_dict).
    """
    breakdown: dict[str, float] = {}
    points = 0.0
    max_points = 100.0

    # Length check (25 pts)
    word_count = len(content.split())
    if doc_type in ("resume_v1", "resume_v2"):
        if word_count >= 300:
            breakdown["length"] = 25
        elif word_count >= 150:
            breakdown["length"] = 15
        else:
            breakdown["length"] = 5
    elif doc_type == "cover_letter":
        if 200 <= word_count <= 500:
            breakdown["length"] = 25
        elif word_count >= 100:
            breakdown["length"] = 15
        else:
            breakdown["length"] = 5
    else:
        breakdown["length"] = 25 if word_count >= 50 else 10
    points += breakdown["length"]

    # Structure check (25 pts)
    paragraph_count = content.count("\n\n") + 1
    if paragraph_count >= 3:
        breakdown["structure"] = 25
    elif paragraph_count >= 2:
        breakdown["structure"] = 15
    else:
        breakdown["structure"] = 5
    points += breakdown["structure"]

    # No placeholder text (25 pts)
    placeholders = ["[", "TODO", "FIXME", "INSERT", "YOUR NAME"]
    placeholder_found = any(p.lower() in content.lower() for p in placeholders)
    breakdown["completeness"] = 5 if placeholder_found else 25
    points += breakdown["completeness"]

    # Content relevance (25 pts)
    if word_count > 20 and len(set(content.lower().split())) > 15:
        breakdown["relevance"] = 25
    else:
        breakdown["relevance"] = 10
    points += breakdown["relevance"]

    score = int(min(100, (points / max_points) * 100))
    return score, breakdown


def run_qa_check(content: str, doc_type: str) -> dict:
    """Run QA checks on generated content. Returns a report dict."""
    issues: list[str] = []
    warnings: list[str] = []
    word_count = len(content.split())

    if word_count < 20:
        issues.append("Content is too short (less than 20 words)")

    placeholders = ["[your", "[insert", "todo:", "fixme"]
    for p in placeholders:
        if p in content.lower():
            issues.append(f"Contains placeholder text: '{p}'")

    words = content.lower().split()
    if words:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:
            warnings.append("High word repetition detected")

    if doc_type == "cover_letter":
        if word_count > 600:
            warnings.append("Cover letter may be too long (>600 words)")
        if "dear" not in content.lower() and "hiring" not in content.lower():
            warnings.append("Cover letter may be missing a proper greeting")

    if doc_type in ("resume_v1", "resume_v2") and word_count < 100:
        warnings.append("Resume seems too short")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "word_count": word_count,
    }


# ---------------------------------------------------------------------------
# Content generation impls (called from Celery tasks)
# ---------------------------------------------------------------------------

async def generate_resume_impl(
    db: AsyncSession,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    profile_id: uuid.UUID,
    instructions: str | None = None,
) -> dict:
    """Generate a tailored resume for a job.

    Creates 2 variants (A and B), runs QA, calculates quality scores,
    and adds to review queue.
    """
    from app.services.ai_proxy_service import call_ai

    job = await _load_job(db, user_id, job_id)
    profile = await _load_profile(db, user_id, profile_id)

    system_prompt = (
        "You are an expert resume writer. Generate a professional, ATS-optimized resume "
        "tailored to the job description. Use clear sections: Summary, Experience, Skills, Education. "
        "Be specific and quantify achievements where possible."
    )
    user_prompt = _build_resume_prompt(job, profile, instructions)

    documents = []
    for variant in ("A", "B"):
        variant_instruction = (
            f"Generate variant {variant}. "
            + ("Use a concise, bullet-point-heavy format." if variant == "A"
               else "Use a narrative format with detailed descriptions.")
        )

        try:
            ai_response = await call_ai(
                db, user_id, "content_resume",
                prompt=user_prompt + "\n\n" + variant_instruction,
                system_prompt=system_prompt,
                max_tokens=4096,
                temperature=0.7,
            )
            content = ai_response.content
        except AppError:
            logger.warning(f"AI call failed for resume variant {variant}, using placeholder")
            content = _placeholder_resume(job, profile, variant)

        doc_type = f"resume_v{1 if variant == 'A' else 2}"
        qa_report = run_qa_check(content, doc_type)
        quality_score, quality_breakdown = calculate_quality_score(content, doc_type)

        doc = Document(
            user_id=user_id,
            job_id=job_id,
            profile_id=profile_id,
            type=doc_type,
            filename=f"resume_{variant.lower()}_{job.company}_{job.title}.md".replace(" ", "_"),
            r2_key=f"users/{user_id}/documents/{uuid.uuid4()}.md",
            content_type="text/markdown",
            file_size=len(content.encode()),
            quality_score=quality_score,
            quality_breakdown=quality_breakdown,
            qa_report=qa_report,
            variant_label=variant,
        )
        db.add(doc)
        await db.flush()

        review_item = ReviewQueue(
            user_id=user_id,
            item_type="resume",
            item_id=doc.id,
            job_id=job_id,
            priority=2,
            status="pending",
        )
        db.add(review_item)
        documents.append({"id": str(doc.id), "variant": variant, "quality_score": quality_score})

    logger.info(f"Generated 2 resume variants for job {job_id}")
    return {"documents": documents, "job_id": str(job_id)}


async def generate_cover_letter_impl(
    db: AsyncSession,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    profile_id: uuid.UUID,
) -> dict:
    """Generate a cover letter for a job."""
    from app.services.ai_proxy_service import call_ai

    job = await _load_job(db, user_id, job_id)
    profile = await _load_profile(db, user_id, profile_id)

    system_prompt = (
        "You are an expert cover letter writer. Write a compelling, personalized cover letter "
        "that connects the candidate's experience to the job requirements. Keep it concise (250-400 words). "
        "Use a professional but engaging tone."
    )
    user_prompt = _build_cover_letter_prompt(job, profile)

    try:
        ai_response = await call_ai(
            db, user_id, "content_cl",
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=2048,
            temperature=0.7,
        )
        content = ai_response.content
    except AppError:
        logger.warning("AI call failed for cover letter, using placeholder")
        content = _placeholder_cover_letter(job, profile)

    qa_report = run_qa_check(content, "cover_letter")
    quality_score, quality_breakdown = calculate_quality_score(content, "cover_letter")

    doc = Document(
        user_id=user_id,
        job_id=job_id,
        profile_id=profile_id,
        type="cover_letter",
        filename=f"cover_letter_{job.company}_{job.title}.md".replace(" ", "_"),
        r2_key=f"users/{user_id}/documents/{uuid.uuid4()}.md",
        content_type="text/markdown",
        file_size=len(content.encode()),
        quality_score=quality_score,
        quality_breakdown=quality_breakdown,
        qa_report=qa_report,
    )
    db.add(doc)
    await db.flush()

    review_item = ReviewQueue(
        user_id=user_id,
        item_type="cover_letter",
        item_id=doc.id,
        job_id=job_id,
        priority=2,
        status="pending",
    )
    db.add(review_item)

    logger.info(f"Generated cover letter for job {job_id}")
    return {"document_id": str(doc.id), "quality_score": quality_score, "job_id": str(job_id)}


async def generate_answers_impl(
    db: AsyncSession,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    questions: list[str],
) -> dict:
    """Generate answers to application questions."""
    from app.services.ai_proxy_service import call_ai

    job = await _load_job(db, user_id, job_id)

    system_prompt = (
        "You are helping a job applicant answer application questions. "
        "Provide concise, professional answers that highlight relevant experience. "
        "Return a JSON array of objects with 'question' and 'answer' keys."
    )
    user_prompt = (
        f"Job: {job.title} at {job.company}\n\n"
        f"Questions:\n" + "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    )

    try:
        ai_response = await call_ai(
            db, user_id, "content_answers",
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=4096,
            temperature=0.5,
        )
        try:
            answers = json.loads(ai_response.content)
        except json.JSONDecodeError:
            answers = [{"question": q, "answer": ai_response.content} for q in questions]
    except AppError:
        logger.warning("AI call failed for answers, using placeholder")
        answers = [{"question": q, "answer": f"Based on my experience, {q.lower()}"} for q in questions]

    content = json.dumps(answers, indent=2)
    doc = Document(
        user_id=user_id,
        job_id=job_id,
        type="answer",
        filename=f"answers_{job.company}_{job.title}.json".replace(" ", "_"),
        r2_key=f"users/{user_id}/documents/{uuid.uuid4()}.json",
        content_type="application/json",
        file_size=len(content.encode()),
    )
    db.add(doc)
    await db.flush()

    review_item = ReviewQueue(
        user_id=user_id,
        item_type="answer",
        item_id=doc.id,
        job_id=job_id,
        priority=3,
        status="pending",
    )
    db.add(review_item)

    logger.info(f"Generated {len(answers)} answers for job {job_id}")
    return {"document_id": str(doc.id), "answers": answers, "job_id": str(job_id)}


async def regenerate_document_impl(
    db: AsyncSession,
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    instructions: str,
) -> dict:
    """Regenerate a document with new instructions."""
    from app.services.ai_proxy_service import call_ai

    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Document not found")

    task_type_map = {
        "resume_v1": "content_resume",
        "resume_v2": "content_resume",
        "cover_letter": "content_cl",
        "answer": "content_answers",
    }
    task_type = task_type_map.get(doc.type, "content_resume")

    system_prompt = (
        f"You are regenerating a {doc.type.replace('_', ' ')} document. "
        f"Follow these additional instructions from the user: {instructions}"
    )

    try:
        ai_response = await call_ai(
            db, user_id, task_type,
            prompt=f"Regenerate this {doc.type} document. Instructions: {instructions}",
            system_prompt=system_prompt,
            max_tokens=4096,
            temperature=0.7,
        )
        content = ai_response.content
    except AppError:
        logger.warning("AI call failed for regeneration, keeping original")
        return {"document_id": str(doc.id), "regenerated": False, "reason": "AI call failed"}

    qa_report = run_qa_check(content, doc.type)
    quality_score, quality_breakdown = calculate_quality_score(content, doc.type)

    doc.quality_score = quality_score
    doc.quality_breakdown = quality_breakdown
    doc.qa_report = qa_report
    doc.file_size = len(content.encode())
    await db.flush()

    logger.info(f"Regenerated document {document_id}")
    return {"document_id": str(doc.id), "quality_score": quality_score, "regenerated": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_job(db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user_id))
    job = result.scalar_one_or_none()
    if not job:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Job not found")
    return job


async def _load_profile(db: AsyncSession, user_id: uuid.UUID, profile_id: uuid.UUID) -> Profile:
    result = await db.execute(
        select(Profile).where(Profile.id == profile_id, Profile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Profile not found")
    return profile


def _build_resume_prompt(job: Job, profile: Profile, instructions: str | None) -> str:
    parts = [
        f"Target Job: {job.title} at {job.company}",
        f"Location: {job.location or 'Not specified'}",
    ]
    if job.description:
        parts.append(f"Job Description:\n{job.description[:2000]}")
    if job.skills_required:
        parts.append(f"Required Skills: {', '.join(job.skills_required)}")
    if job.skills_preferred:
        parts.append(f"Preferred Skills: {', '.join(job.skills_preferred)}")
    parts.append(f"\nCandidate Profile: {profile.target_role}")
    if profile.current_title:
        parts.append(f"Current Title: {profile.current_title}")
    if profile.bio_snippet:
        parts.append(f"Bio: {profile.bio_snippet}")
    if instructions:
        parts.append(f"\nAdditional Instructions: {instructions}")
    return "\n".join(parts)


def _build_cover_letter_prompt(job: Job, profile: Profile) -> str:
    parts = [
        f"Write a cover letter for: {job.title} at {job.company}",
        f"Location: {job.location or 'Not specified'}",
    ]
    if job.description:
        parts.append(f"Job Description:\n{job.description[:2000]}")
    parts.append(f"\nCandidate: {profile.target_role}")
    if profile.current_title:
        parts.append(f"Current Title: {profile.current_title}")
    if profile.bio_snippet:
        parts.append(f"Bio: {profile.bio_snippet}")
    if profile.ai_instructions:
        parts.append(f"Tone/Style: {profile.ai_instructions}")
    return "\n".join(parts)


def _placeholder_resume(job: Job, profile: Profile, variant: str) -> str:
    """Fallback resume when AI is unavailable."""
    skills = job.skills_required or ["Python", "SQL"]
    skills_text = "\n".join(f"- {s}" for s in skills)
    return (
        f"# {profile.target_role} Resume (Variant {variant})\n\n"
        f"## Professional Summary\n\n"
        f"Experienced {profile.target_role} seeking {job.title} position at {job.company}.\n\n"
        f"## Skills\n\n{skills_text}\n\n"
        f"## Experience\n\n"
        f"Professional experience in {profile.target_role} with demonstrated results.\n\n"
        f"## Education\n\n"
        f"Relevant degree and certifications.\n"
    )


def _placeholder_cover_letter(job: Job, profile: Profile) -> str:
    """Fallback cover letter when AI is unavailable."""
    return (
        f"Dear Hiring Manager,\n\n"
        f"I am writing to express my interest in the {job.title} position at {job.company}. "
        f"As an experienced {profile.target_role}, I am confident in my ability to contribute "
        f"to your team.\n\n"
        f"My background aligns well with the requirements of this role, and I am eager to bring "
        f"my skills and experience to {job.company}.\n\n"
        f"I look forward to discussing how I can contribute to your team.\n\n"
        f"Best regards"
    )
