"""Copilot service — AI chat with streaming, conversation management, action execution.

Implements copilot logic per API Contract Section 4.9.
"""

import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.copilot_conversation import CopilotConversation


async def chat_stream(
    db: AsyncSession, user_id: uuid.UUID, message: str,
    context: dict | None, conversation_id: uuid.UUID | None,
) -> AsyncGenerator[str, None]:
    """Stream a copilot response via SSE. Yields text chunks."""
    raise NotImplementedError
    yield  # type: ignore[misc]  # make this a generator


async def list_conversations(db: AsyncSession, user_id: uuid.UUID) -> list[CopilotConversation]:
    """List all conversations for a user."""
    raise NotImplementedError


async def delete_conversation(db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
    """Delete a conversation."""
    raise NotImplementedError


async def execute_action(db: AsyncSession, user_id: uuid.UUID, action: str, params: dict, token: str) -> dict:
    """Execute a copilot-suggested action after user confirmation."""
    raise NotImplementedError
