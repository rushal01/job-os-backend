"""Copilot API endpoints — API Contract Section 4.9.

4 endpoints: chat (SSE), list conversations, delete conversation, execute action.
"""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
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
from app.services import copilot_service

router = APIRouter(prefix="/copilot")


@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream a copilot chat response via SSE."""

    async def generate():
        async for chunk in copilot_service.chat_stream(
            db, current_user.id, body.message, body.context, body.conversation_id
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/conversations", response_model=DataResponse[list[ConversationResponse]])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all copilot conversations for the current user."""
    conversations = await copilot_service.list_conversations(db, current_user.id)
    return {"data": conversations}


@router.delete("/conversations/{conversation_id}", response_model=SuccessResponse)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a copilot conversation."""
    await copilot_service.delete_conversation(db, current_user.id, conversation_id)
    return {"success": True}


@router.post("/execute", response_model=ExecuteResponse)
async def execute_action(
    body: ExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Execute a copilot-suggested action with confirmation."""
    result = await copilot_service.execute_action(
        db, current_user.id, body.action, body.params, body.confirmation_token
    )
    return result
