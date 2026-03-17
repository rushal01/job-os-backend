"""Content Generation API endpoints — API Contract Section 4.4.

4 endpoints: generate-resume, generate-cover-letter, generate-answers, regenerate.
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, TaskResponse
from app.services import content_service

router = APIRouter(prefix="/content")

RESUME_TEMPLATES = [
    {"id": "professional", "name": "Professional", "description": "Clean, ATS-friendly format"},
    {"id": "modern", "name": "Modern", "description": "Contemporary design with sidebar"},
    {"id": "minimal", "name": "Minimal", "description": "Simple and elegant"},
    {"id": "technical", "name": "Technical", "description": "Optimized for engineering roles"},
]


@router.get("/templates", response_model=DataResponse[list[dict]])
async def get_templates() -> dict:
    """Return the static list of available resume templates."""
    return {"data": RESUME_TEMPLATES}


class _GenerateResumeBody(BaseModel):
    job_id: uuid.UUID
    profile_id: uuid.UUID
    instructions: str | None = None


class _GenerateCoverLetterBody(BaseModel):
    job_id: uuid.UUID
    profile_id: uuid.UUID


class _GenerateAnswersBody(BaseModel):
    job_id: uuid.UUID
    questions: list[str]


class _RegenerateBody(BaseModel):
    document_id: uuid.UUID
    instructions: str


@router.get("/variants/{job_id}", response_model=DataResponse[list[dict]])
async def get_content_variants(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all generated content variants for a job."""
    from sqlalchemy import select

    from app.models.document import Document
    from app.schemas.common import DataResponse

    result = await db.execute(
        select(Document).where(
            Document.job_id == job_id,
            Document.user_id == current_user.id,
        ).order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    variants = []
    for doc in documents:
        variants.append({
            "id": str(doc.id),
            "type": doc.type,
            "filename": doc.filename,
            "variant_label": doc.variant_label,
            "quality_score": doc.quality_score,
            "quality_breakdown": doc.quality_breakdown,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        })

    return {"data": variants}


@router.post("/generate-resume", response_model=TaskResponse)
async def generate_resume(
    body: _GenerateResumeBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Trigger async resume generation tailored to a specific job."""
    task_id = await content_service.generate_resume(
        db, current_user.id, body.job_id, body.profile_id, body.instructions,
    )
    await db.commit()
    return TaskResponse(task_id=task_id)


@router.post("/generate-cover-letter", response_model=TaskResponse)
async def generate_cover_letter(
    body: _GenerateCoverLetterBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Trigger async cover letter generation."""
    task_id = await content_service.generate_cover_letter(
        db, current_user.id, body.job_id, body.profile_id,
    )
    await db.commit()
    return TaskResponse(task_id=task_id)


@router.post("/generate-answers", response_model=TaskResponse)
async def generate_answers(
    body: _GenerateAnswersBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Trigger async application question answering."""
    task_id = await content_service.generate_answers(
        db, current_user.id, body.job_id, body.questions,
    )
    await db.commit()
    return TaskResponse(task_id=task_id)


@router.post("/regenerate", response_model=TaskResponse)
async def regenerate_content(
    body: _RegenerateBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Regenerate a document with new instructions."""
    task_id = await content_service.regenerate_document(
        db, current_user.id, body.document_id, body.instructions,
    )
    await db.commit()
    return TaskResponse(task_id=task_id)
