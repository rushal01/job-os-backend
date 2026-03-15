"""Copilot schemas — API Contract Section 4.9.

Defines request/response models for the AI copilot chat interface.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """POST /copilot/chat request body."""

    message: str
    context: dict | None = None
    conversation_id: uuid.UUID | None = None


class CopilotMessage(BaseModel):
    """A single message in a copilot conversation."""

    role: str  # user, assistant
    content: str
    timestamp: datetime | None = None


class ConversationResponse(BaseModel):
    """Conversation summary for GET /copilot/conversations."""

    id: uuid.UUID
    user_id: uuid.UUID
    messages: list[dict] = []
    model_used: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExecuteRequest(BaseModel):
    """POST /copilot/execute request body."""

    action: str
    params: dict = {}
    confirmation_token: str


class ExecuteResponse(BaseModel):
    """Response from POST /copilot/execute."""

    task_id: str | None = None
    result: dict | None = None
