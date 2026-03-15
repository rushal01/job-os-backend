"""Admin schemas — API Contract Section 4.13.

Defines request/response models for super admin endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AdminUser(BaseModel):
    """Admin view of a user."""

    id: uuid.UUID
    email: str
    role: str
    full_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserDetail(BaseModel):
    """Detailed admin view of a user."""

    id: uuid.UUID
    email: str
    role: str
    full_name: str | None = None
    timezone: str
    settings: dict = {}
    supabase_uid: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleUpdate(BaseModel):
    """PUT /admin/users/:id/role request body."""

    role: str


class SuspendRequest(BaseModel):
    """PUT /admin/users/:id/suspend request body."""

    reason: str


class SystemHealth(BaseModel):
    """System health overview for admins."""

    database: str = "unknown"
    redis: str = "unknown"
    celery_workers: int = 0
    queue_depth: int = 0
    uptime_seconds: float = 0.0


class FeatureFlags(BaseModel):
    """Feature flag configuration."""

    flags: dict = {}


class FeatureFlagUpdate(BaseModel):
    """PUT /admin/feature-flags request body."""

    flags: dict
