"""Email Intelligence API endpoints.

Referenced by file tree spec: app/api/v1/email.py
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, TaskResponse
from app.schemas.email import EmailScanResult, EmailSettings

router = APIRouter(prefix="/email")


@router.get("/settings", response_model=DataResponse[EmailSettings])
async def get_email_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[EmailSettings]:
    """Get email integration settings."""
    raise NotImplementedError


@router.put("/settings", response_model=DataResponse[EmailSettings])
async def update_email_settings(
    body: EmailSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[EmailSettings]:
    """Update email integration settings."""
    raise NotImplementedError


@router.post("/scan", response_model=TaskResponse)
async def trigger_email_scan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Trigger an async email scan for job-related emails."""
    raise NotImplementedError
