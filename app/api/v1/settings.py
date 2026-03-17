"""Settings API — user preferences, scoring weights, automation config, job sources."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse

router = APIRouter(prefix="/settings")


class UserSettings(BaseModel):
    """Complete user settings."""
    theme: str = "system"
    notification_preferences: dict = {}
    scoring_weights: dict = {}
    automation_config: dict = {}
    job_sources: dict = {}
    email_settings: dict = {}
    feature_flags: dict = {}
    schedules: dict = {}


@router.get("", response_model=DataResponse[dict])
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Get all settings for the current user."""
    return DataResponse(data=current_user.settings or {})


@router.put("", response_model=DataResponse[dict])
async def update_settings(
    body: UserSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Update user settings (merge with existing)."""
    existing = current_user.settings or {}
    updates = body.model_dump(exclude_unset=True)
    existing.update(updates)
    current_user.settings = existing
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(current_user, "settings")
    await db.commit()
    await db.refresh(current_user)
    return DataResponse(data=current_user.settings)


@router.get("/{section}", response_model=DataResponse[dict])
async def get_settings_section(
    section: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Get a specific settings section."""
    settings = current_user.settings or {}
    return DataResponse(data=settings.get(section, {}))


@router.put("/{section}", response_model=DataResponse[dict])
async def update_settings_section(
    section: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Update a specific settings section."""
    settings = current_user.settings or {}
    settings[section] = body
    current_user.settings = settings
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(current_user, "settings")
    await db.commit()
    await db.refresh(current_user)
    return DataResponse(data=settings[section])
