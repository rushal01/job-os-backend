"""Email Intelligence API endpoints.

Referenced by file tree spec: app/api/v1/email.py
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, TaskResponse
from app.schemas.email import EmailSettings
from app.services import email_service

router = APIRouter(prefix="/email")


@router.get("/settings", response_model=DataResponse[EmailSettings])
async def get_email_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[EmailSettings]:
    """Get email integration settings."""
    settings = await email_service.get_email_settings(db, current_user.id)
    return DataResponse(data=EmailSettings(**settings))


@router.put("/settings", response_model=DataResponse[EmailSettings])
async def update_email_settings(
    body: EmailSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[EmailSettings]:
    """Update email integration settings."""
    updated = await email_service.update_email_settings(
        db, current_user.id, body.model_dump()
    )
    return DataResponse(data=EmailSettings(**updated))


@router.post("/scan", response_model=TaskResponse)
async def trigger_email_scan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Trigger an async email scan for job-related emails."""
    task_id = await email_service.trigger_email_scan(db, current_user.id)
    return TaskResponse(task_id=task_id)
