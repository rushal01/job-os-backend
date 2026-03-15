"""AI Provider Management API endpoints — API Contract Section 4.8.

7 endpoints: list keys, add key, delete key, validate key, list models, update models, usage.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, ErrorCode
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import (
    APIKeyCreate,
    APIKeyInfo,
    APIKeyValidation,
    ModelConfig,
    ModelConfigUpdate,
    UsageStats,
)
from app.schemas.common import DataResponse, SuccessResponse
from app.services import ai_proxy_service

router = APIRouter(prefix="/ai")


@router.get("/keys", response_model=DataResponse[list[APIKeyInfo]])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all API keys (masked) for the current user."""
    keys = await ai_proxy_service.list_api_keys(db, current_user.id)
    return {"data": keys}


@router.post("/keys", status_code=status.HTTP_201_CREATED, response_model=DataResponse[APIKeyInfo])
async def add_api_key(
    body: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add and encrypt a new API key."""
    key = await ai_proxy_service.add_api_key(db, current_user.id, body.provider, body.api_key)
    # Return masked version
    masked_key = f"{'*' * 8}...{body.api_key[-8:]}" if len(body.api_key) >= 8 else body.api_key
    return {"data": {
        "id": key.id,
        "provider": key.provider,
        "status": key.status,
        "last_validated": key.last_validated,
        "masked_key": masked_key,
        "created_at": key.created_at,
    }}


@router.delete("/keys/{key_id}", response_model=SuccessResponse)
async def delete_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an API key."""
    found = await ai_proxy_service.delete_api_key(db, current_user.id, key_id)
    if not found:
        raise AppError(code=ErrorCode.RESOURCE_NOT_FOUND, message="API key not found")
    return {"success": True}


@router.post("/keys/{key_id}/validate", response_model=APIKeyValidation)
async def validate_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate an API key by making a test call to the provider."""
    return await ai_proxy_service.validate_api_key(db, current_user.id, key_id)


@router.get("/models", response_model=DataResponse[list[ModelConfig]])
async def list_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List configured AI models per task type."""
    configs = await ai_proxy_service.get_model_config(db, current_user.id)
    return {"data": configs}


@router.put("/models", response_model=DataResponse[list[ModelConfig]])
async def update_models(
    body: ModelConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update AI model configuration."""
    configs = await ai_proxy_service.update_model_config(db, current_user.id, body.task_model_map)
    return {"data": configs}


@router.get("/usage", response_model=DataResponse[UsageStats])
async def get_usage(
    period: str = Query(default="30d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get AI usage statistics for a period."""
    stats = await ai_proxy_service.get_usage_stats(db, current_user.id, period)
    return {"data": stats}
