"""Auth request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None


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
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserSchema
    session: SessionSchema


class SessionResponse(BaseModel):
    session: SessionSchema


class UserResponse(BaseModel):
    user: UserSchema
