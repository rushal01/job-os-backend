"""Copilot API endpoints — API Contract Section 4.9.

4 endpoints: chat (SSE), list conversations, delete conversation, execute action.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, SuccessResponse
from app.schemas.copilot import (
    ChatRequest,
    ConversationResponse,
    ExecuteRequest,
    ExecuteResponse,
)

router = APIRouter(prefix="/copilot")


@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream a copilot chat response via SSE."""
    raise NotImplementedError


@router.get("/conversations", response_model=DataResponse[list[ConversationResponse]])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[ConversationResponse]]:
    """List all copilot conversations for the current user."""
    raise NotImplementedError


@router.delete("/conversations/{conversation_id}", response_model=SuccessResponse)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """Delete a copilot conversation."""
    raise NotImplementedError


@router.post("/execute", response_model=ExecuteResponse)
async def execute_action(
    body: ExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExecuteResponse:
    """Execute a copilot-suggested action with confirmation."""
    raise NotImplementedError
