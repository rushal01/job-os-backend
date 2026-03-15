"""Outreach API endpoints — contacts and message management.

Referenced by file tree spec: app/api/v1/outreach.py
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, SuccessResponse
from app.schemas.outreach import (
    OutreachContactCreate,
    OutreachContactResponse,
    OutreachContactUpdate,
    OutreachMessageCreate,
    OutreachMessageResponse,
)

router = APIRouter(prefix="/outreach")


@router.get("/contacts", response_model=DataResponse[list[OutreachContactResponse]])
async def list_contacts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[OutreachContactResponse]]:
    """List all outreach contacts for the current user."""
    raise NotImplementedError


@router.post("/contacts", status_code=status.HTTP_201_CREATED, response_model=DataResponse[OutreachContactResponse])
async def create_contact(
    body: OutreachContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[OutreachContactResponse]:
    """Create a new outreach contact."""
    raise NotImplementedError


@router.put("/contacts/{contact_id}", response_model=DataResponse[OutreachContactResponse])
async def update_contact(
    contact_id: uuid.UUID,
    body: OutreachContactUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[OutreachContactResponse]:
    """Update an outreach contact."""
    raise NotImplementedError


@router.delete("/contacts/{contact_id}", response_model=SuccessResponse)
async def delete_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """Soft-delete an outreach contact."""
    raise NotImplementedError


@router.post("/messages", status_code=status.HTTP_201_CREATED, response_model=DataResponse[OutreachMessageResponse])
async def create_message(
    body: OutreachMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[OutreachMessageResponse]:
    """Create a new outreach message."""
    raise NotImplementedError


@router.get("/contacts/{contact_id}/messages", response_model=DataResponse[list[OutreachMessageResponse]])
async def list_contact_messages(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[OutreachMessageResponse]]:
    """List all messages for a contact."""
    raise NotImplementedError
