"""Outreach service — manage contacts and messages for recruiter/referral outreach.

Note: The API routes in api/v1/outreach.py implement most operations inline.
These service functions provide the same logic for use by tasks or other services.
"""

import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.models.outreach_contact import OutreachContact
from app.models.outreach_message import OutreachMessage


async def list_contacts(db: AsyncSession, user_id: uuid.UUID) -> list[OutreachContact]:
    """List all non-deleted outreach contacts."""
    result = await db.execute(
        select(OutreachContact).where(
            OutreachContact.user_id == user_id,
            OutreachContact.is_deleted == False,  # noqa: E712
        ).order_by(OutreachContact.created_at.desc())
    )
    return list(result.scalars().all())


async def create_contact(db: AsyncSession, user_id: uuid.UUID, data: dict) -> OutreachContact:
    """Create a new outreach contact."""
    contact = OutreachContact(
        user_id=user_id,
        job_id=data.get("job_id"),
        name=data["name"],
        title=data.get("title"),
        company=data.get("company"),
        linkedin_url=data.get("linkedin_url"),
        email=data.get("email"),
        channel=data.get("channel"),
        warmth=data.get("warmth"),
        status="draft",
    )
    db.add(contact)
    await db.flush()
    await db.refresh(contact)
    logger.info(f"Created outreach contact {contact.id} for user {user_id}")
    return contact


async def update_contact(
    db: AsyncSession, user_id: uuid.UUID, contact_id: uuid.UUID, data: dict,
) -> OutreachContact:
    """Update an outreach contact."""
    result = await db.execute(
        select(OutreachContact).where(
            OutreachContact.id == contact_id,
            OutreachContact.user_id == user_id,
            OutreachContact.is_deleted == False,  # noqa: E712
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Contact not found")

    for field, value in data.items():
        if hasattr(contact, field):
            setattr(contact, field, value)

    await db.flush()
    logger.info(f"Updated outreach contact {contact_id}")
    return contact


async def delete_contact(db: AsyncSession, user_id: uuid.UUID, contact_id: uuid.UUID) -> None:
    """Soft-delete an outreach contact."""
    result = await db.execute(
        select(OutreachContact).where(
            OutreachContact.id == contact_id,
            OutreachContact.user_id == user_id,
            OutreachContact.is_deleted == False,  # noqa: E712
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Contact not found")

    contact.is_deleted = True
    await db.flush()
    logger.info(f"Soft-deleted outreach contact {contact_id}")


async def create_message(db: AsyncSession, user_id: uuid.UUID, data: dict) -> OutreachMessage:
    """Create a new outreach message."""
    # Verify contact belongs to user
    result = await db.execute(
        select(OutreachContact).where(
            OutreachContact.id == data["contact_id"],
            OutreachContact.user_id == user_id,
            OutreachContact.is_deleted == False,  # noqa: E712
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Contact not found")

    message = OutreachMessage(
        contact_id=data["contact_id"],
        content=data.get("content", ""),
        channel=data.get("channel"),
        is_follow_up=data.get("is_follow_up", False),
        follow_up_number=data.get("follow_up_number"),
        status="draft",
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    logger.info(f"Created outreach message {message.id} for contact {data['contact_id']}")
    return message


async def list_contact_messages(
    db: AsyncSession, user_id: uuid.UUID, contact_id: uuid.UUID,
) -> list[OutreachMessage]:
    """List all messages for a contact."""
    # Verify contact belongs to user
    result = await db.execute(
        select(OutreachContact).where(
            OutreachContact.id == contact_id,
            OutreachContact.user_id == user_id,
            OutreachContact.is_deleted == False,  # noqa: E712
        )
    )
    if not result.scalar_one_or_none():
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="Contact not found")

    result = await db.execute(
        select(OutreachMessage).where(
            OutreachMessage.contact_id == contact_id,
        ).order_by(OutreachMessage.created_at.asc())
    )
    return list(result.scalars().all())
