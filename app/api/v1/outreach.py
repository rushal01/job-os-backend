"""Outreach API endpoints — contacts and message management.

Referenced by file tree spec: app/api/v1/outreach.py
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.outreach_contact import OutreachContact
from app.models.outreach_message import OutreachMessage
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


@router.get("/stats", response_model=DataResponse[dict])
async def get_outreach_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[dict]:
    """Get outreach statistics."""
    from sqlalchemy import func

    total = (await db.execute(
        select(func.count(OutreachContact.id)).where(
            OutreachContact.user_id == current_user.id,
            OutreachContact.is_deleted == False,  # noqa: E712
        )
    )).scalar() or 0

    by_warmth = {}
    warmth_result = await db.execute(
        select(OutreachContact.warmth, func.count(OutreachContact.id)).where(
            OutreachContact.user_id == current_user.id,
            OutreachContact.is_deleted == False,  # noqa: E712
        ).group_by(OutreachContact.warmth)
    )
    for row in warmth_result.all():
        by_warmth[row[0] or "unknown"] = row[1]

    by_status = {}
    status_result = await db.execute(
        select(OutreachContact.status, func.count(OutreachContact.id)).where(
            OutreachContact.user_id == current_user.id,
            OutreachContact.is_deleted == False,  # noqa: E712
        ).group_by(OutreachContact.status)
    )
    for row in status_result.all():
        by_status[row[0] or "unknown"] = row[1]

    # Count messages
    total_messages = (await db.execute(
        select(func.count(OutreachMessage.id))
        .join(OutreachContact, OutreachContact.id == OutreachMessage.contact_id)
        .where(
            OutreachContact.user_id == current_user.id,
            OutreachContact.is_deleted == False,  # noqa: E712
        )
    )).scalar() or 0

    return {"data": {
        "total_contacts": total,
        "by_warmth": by_warmth,
        "by_status": by_status,
        "total_messages": total_messages,
    }}


@router.get("/follow-ups", response_model=DataResponse[list[OutreachMessageResponse]])
async def get_follow_ups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[OutreachMessageResponse]]:
    """Get pending follow-up messages."""
    result = await db.execute(
        select(OutreachMessage)
        .join(OutreachContact, OutreachContact.id == OutreachMessage.contact_id)
        .where(
            OutreachContact.user_id == current_user.id,
            OutreachContact.is_deleted == False,  # noqa: E712
            OutreachMessage.is_follow_up == True,  # noqa: E712
            OutreachMessage.status == "draft",
        ).order_by(OutreachMessage.created_at.desc())
    )
    messages = result.scalars().all()
    return {"data": messages}


@router.get("/contacts", response_model=DataResponse[list[OutreachContactResponse]])
async def list_contacts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[OutreachContactResponse]]:
    """List all outreach contacts for the current user."""
    result = await db.execute(
        select(OutreachContact).where(
            OutreachContact.user_id == current_user.id,
            OutreachContact.is_deleted == False,  # noqa: E712
        ).order_by(OutreachContact.created_at.desc())
    )
    contacts = result.scalars().all()
    return {"data": contacts}


@router.post("/contacts", status_code=status.HTTP_201_CREATED, response_model=DataResponse[OutreachContactResponse])
async def create_contact(
    body: OutreachContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[OutreachContactResponse]:
    """Create a new outreach contact."""
    contact = OutreachContact(
        user_id=current_user.id,
        job_id=body.job_id,
        name=body.name,
        title=body.title,
        company=body.company,
        linkedin_url=body.linkedin_url,
        email=body.email,
        channel=body.channel,
        warmth=body.warmth,
        status="draft",
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return {"data": contact}


@router.put("/contacts/{contact_id}", response_model=DataResponse[OutreachContactResponse])
async def update_contact(
    contact_id: uuid.UUID,
    body: OutreachContactUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[OutreachContactResponse]:
    """Update an outreach contact."""
    result = await db.execute(
        select(OutreachContact).where(
            OutreachContact.id == contact_id,
            OutreachContact.user_id == current_user.id,
            OutreachContact.is_deleted == False,  # noqa: E712
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Contact not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    await db.commit()
    await db.refresh(contact)
    return {"data": contact}


@router.delete("/contacts/{contact_id}", response_model=SuccessResponse)
async def delete_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """Soft-delete an outreach contact."""
    result = await db.execute(
        select(OutreachContact).where(
            OutreachContact.id == contact_id,
            OutreachContact.user_id == current_user.id,
            OutreachContact.is_deleted == False,  # noqa: E712
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Contact not found")

    contact.is_deleted = True
    await db.commit()
    return {"success": True}


@router.post("/messages", status_code=status.HTTP_201_CREATED, response_model=DataResponse[OutreachMessageResponse])
async def create_message(
    body: OutreachMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[OutreachMessageResponse]:
    """Create a new outreach message."""
    # Verify the contact belongs to the current user
    result = await db.execute(
        select(OutreachContact).where(
            OutreachContact.id == body.contact_id,
            OutreachContact.user_id == current_user.id,
            OutreachContact.is_deleted == False,  # noqa: E712
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Contact not found")

    message = OutreachMessage(
        contact_id=body.contact_id,
        content=body.content,
        channel=body.channel,
        is_follow_up=body.is_follow_up,
        follow_up_number=body.follow_up_number,
        status="draft",
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return {"data": message}


@router.get("/contacts/{contact_id}/messages", response_model=DataResponse[list[OutreachMessageResponse]])
async def list_contact_messages(
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[OutreachMessageResponse]]:
    """List all messages for a contact."""
    # Verify the contact belongs to the current user
    result = await db.execute(
        select(OutreachContact).where(
            OutreachContact.id == contact_id,
            OutreachContact.user_id == current_user.id,
            OutreachContact.is_deleted == False,  # noqa: E712
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Contact not found")

    result = await db.execute(
        select(OutreachMessage).where(
            OutreachMessage.contact_id == contact_id,
        ).order_by(OutreachMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return {"data": messages}
