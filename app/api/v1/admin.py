"""Admin API endpoints — API Contract Section 4.13.

7 endpoints: list users, get user, update role, suspend, system health, feature flags (get/put).
All require super_admin role.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminUser,
    AdminUserDetail,
    FeatureFlags,
    FeatureFlagUpdate,
    RoleUpdate,
    SuspendRequest,
    SystemHealth,
)
from app.schemas.common import DataResponse, PaginatedResponse

router = APIRouter(prefix="/admin")


@router.get("/users", response_model=PaginatedResponse[AdminUser])
async def list_users(
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AdminUser]:
    """List all users (admin only)."""
    raise NotImplementedError


@router.get("/users/{user_id}", response_model=DataResponse[AdminUserDetail])
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AdminUserDetail]:
    """Get detailed user info (admin only)."""
    raise NotImplementedError


@router.put("/users/{user_id}/role", response_model=DataResponse[AdminUser])
async def update_user_role(
    user_id: uuid.UUID,
    body: RoleUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AdminUser]:
    """Update a user's role (admin only)."""
    raise NotImplementedError


@router.put("/users/{user_id}/suspend", response_model=DataResponse[AdminUser])
async def suspend_user(
    user_id: uuid.UUID,
    body: SuspendRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AdminUser]:
    """Suspend a user account (admin only)."""
    raise NotImplementedError


@router.get("/system-health", response_model=DataResponse[SystemHealth])
async def get_system_health(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[SystemHealth]:
    """Get system health overview (admin only)."""
    raise NotImplementedError


@router.get("/feature-flags", response_model=DataResponse[FeatureFlags])
async def get_feature_flags(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[FeatureFlags]:
    """Get feature flag configuration (admin only)."""
    raise NotImplementedError


@router.put("/feature-flags", response_model=DataResponse[FeatureFlags])
async def update_feature_flags(
    body: FeatureFlagUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[FeatureFlags]:
    """Update feature flags (admin only)."""
    raise NotImplementedError
