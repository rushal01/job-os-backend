"""Application service — tracking, submission, and status management.

Implements business logic for application tracking per API Contract Section 4.5.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application


async def list_applications(
    db: AsyncSession, user_id: uuid.UUID, cursor: str | None, limit: int, filters: dict,
) -> tuple[list[Application], str | None, bool]:
    """List applications with cursor pagination. Returns (apps, next_cursor, has_more)."""
    raise NotImplementedError


async def get_application(db: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID) -> Application | None:
    """Get an application by ID, enforcing user ownership."""
    raise NotImplementedError


async def submit_application(db: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID) -> str:
    """Queue ATS auto-submission via Playwright. Returns task_id."""
    raise NotImplementedError


async def mark_applied(db: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID, method: str, notes: str | None) -> Application:
    """Manually mark an application as applied."""
    raise NotImplementedError


async def update_status(db: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID, status: str) -> Application:
    """Update application status."""
    raise NotImplementedError


async def undo_application(db: AsyncSession, user_id: uuid.UUID, application_id: uuid.UUID) -> Application:
    """Undo the last status change (revert to previous status)."""
    raise NotImplementedError
