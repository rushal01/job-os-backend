"""Auth request/response schemas."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class SessionSchema(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class UserSchema(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None = None
    role: str
    avatar_url: str | None = None
    timezone: str
    has_completed_onboarding: bool = False
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserSchema
    session: SessionSchema


class SessionResponse(BaseModel):
    session: SessionSchema


class UserResponse(BaseModel):
    user: UserSchema


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    timezone: str | None = None
    avatar_url: str | None = None
    has_completed_onboarding: bool | None = None
    settings: dict | None = None
