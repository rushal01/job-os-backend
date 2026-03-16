"""Auth API endpoints — signup, login, logout, refresh, /me."""

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    SessionResponse,
    SessionSchema,
    SignupRequest,
    UserResponse,
    UserSchema,
    UserUpdateRequest,
)
from app.schemas.common import SuccessResponse
from app.services import auth_service

router = APIRouter(prefix="/auth")


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user via Supabase Auth and create a local record."""
    supa_resp = await auth_service.supabase_signup(body.email, body.password)

    supabase_uid = supa_resp["user"]["id"]

    user = await auth_service.create_user(
        db=db,
        email=body.email,
        supabase_uid=supabase_uid,
        full_name=body.full_name,
    )
    await db.commit()
    await db.refresh(user)

    return AuthResponse(
        user=UserSchema.model_validate(user),
        session=SessionSchema(**supa_resp["session"]),
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate via Supabase Auth and return user + session."""
    supa_resp = await auth_service.supabase_login(body.email, body.password)

    supabase_uid = supa_resp["user"]["id"]
    user = await auth_service.get_user_by_supabase_uid(db, supabase_uid)

    if user is None:
        # First login — create local record (user may have signed up via Supabase directly)
        user = await auth_service.create_user(
            db=db,
            email=body.email,
            supabase_uid=supabase_uid,
        )
        await db.commit()
        await db.refresh(user)

    session_data = supa_resp.get("session", supa_resp)
    return AuthResponse(
        user=UserSchema.model_validate(user),
        session=SessionSchema(
            access_token=session_data.get("access_token", ""),
            refresh_token=session_data.get("refresh_token", ""),
            expires_in=session_data.get("expires_in", 3600),
            token_type=session_data.get("token_type", "bearer"),
        ),
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """Revoke the current session via Supabase Auth."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    try:
        await auth_service.supabase_logout(token)
    except Exception as exc:
        from loguru import logger

        logger.warning(f"Logout revocation failed (best-effort): {exc}")
    return SuccessResponse()


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    body: RefreshRequest,
    current_user: User = Depends(get_current_user),
):
    """Refresh the session via Supabase Auth."""
    result = await auth_service.supabase_refresh(body.refresh_token)
    return SessionResponse(session=SessionSchema(**result["session"]))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return UserResponse(user=UserSchema.model_validate(current_user))


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the currently authenticated user's profile/settings."""
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return UserResponse(user=UserSchema.model_validate(current_user))


@router.get("/settings", response_model=UserResponse)
async def get_settings(current_user: User = Depends(get_current_user)):
    """Return user settings (alias for /me)."""
    return UserResponse(user=UserSchema.model_validate(current_user))


@router.put("/settings", response_model=UserResponse)
async def update_settings(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user settings."""
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return UserResponse(user=UserSchema.model_validate(current_user))


@router.get("/debug-config")
async def debug_config():
    """Temporary diagnostic endpoint — shows masked JWT secret config.

    Remove this endpoint once auth is working.
    """
    from app.config import settings

    secret = settings.SUPABASE_JWT_SECRET
    return {
        "jwt_secret_length": len(secret),
        "jwt_secret_first4": secret[:4],
        "jwt_secret_last4": secret[-4:],
        "supabase_url": settings.SUPABASE_URL,
        "cors_origins": settings.cors_origins_list,
        "environment": settings.ENVIRONMENT,
    }
