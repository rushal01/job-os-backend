"""Outreach service — manage contacts and messages for recruiter/referral outreach."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outreach_contact import OutreachContact
from app.models.outreach_message import OutreachMessage


async def list_contacts(db: AsyncSession, user_id: uuid.UUID) -> list[OutreachContact]:
    """List all non-deleted outreach contacts."""
    raise NotImplementedError


async def create_contact(db: AsyncSession, user_id: uuid.UUID, data: dict) -> OutreachContact:
    """Create a new outreach contact."""
    raise NotImplementedError


async def update_contact(db: AsyncSession, user_id: uuid.UUID, contact_id: uuid.UUID, data: dict) -> OutreachContact:
    """Update an outreach contact."""
    raise NotImplementedError


async def delete_contact(db: AsyncSession, user_id: uuid.UUID, contact_id: uuid.UUID) -> None:
    """Soft-delete an outreach contact."""
    raise NotImplementedError


async def create_message(db: AsyncSession, user_id: uuid.UUID, data: dict) -> OutreachMessage:
    """Create a new outreach message."""
    raise NotImplementedError


async def list_contact_messages(db: AsyncSession, user_id: uuid.UUID, contact_id: uuid.UUID) -> list[OutreachMessage]:
    """List all messages for a contact."""
    raise NotImplementedError
