"""Integration tests for Auth API endpoints (Sprint 1.1).

Tests: signup, login, logout, refresh, and /me.
Supabase Auth calls are mocked — we test our API logic and DB interactions.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ErrorCode
from app.models.user import User, UserRole

SIGNUP_URL = "/api/v1/auth/signup"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
REFRESH_URL = "/api/v1/auth/refresh"
ME_URL = "/api/v1/auth/me"

# Fake Supabase responses
FAKE_SUPABASE_UID = "supa-uid-" + uuid.uuid4().hex[:8]
FAKE_ACCESS_TOKEN = "fake-access-token"
FAKE_REFRESH_TOKEN = "fake-refresh-token"


def _supabase_signup_response(email: str, uid: str = FAKE_SUPABASE_UID):
    return {
        "user": {"id": uid, "email": email},
        "session": {
            "access_token": FAKE_ACCESS_TOKEN,
            "refresh_token": FAKE_REFRESH_TOKEN,
            "expires_in": 3600,
            "token_type": "bearer",
        },
    }


def _supabase_login_response(email: str, uid: str = FAKE_SUPABASE_UID):
    return _supabase_signup_response(email, uid)


def _supabase_refresh_response():
    return {
        "session": {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
            "token_type": "bearer",
        },
    }


@pytest.mark.asyncio
async def test_signup_success(async_client: AsyncClient, db_session: AsyncSession):
    """POST /auth/signup with valid data creates user and returns session."""
    email = "newuser@example.com"

    with patch(
        "app.services.auth_service.supabase_signup",
        new_callable=AsyncMock,
        return_value=_supabase_signup_response(email),
    ):
        resp = await async_client.post(
            SIGNUP_URL,
            json={"email": email, "password": "StrongP@ss1!", "full_name": "New User"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert "user" in body
    assert "session" in body
    assert body["user"]["email"] == email
    assert body["user"]["full_name"] == "New User"
    assert body["session"]["access_token"] == FAKE_ACCESS_TOKEN

    # Verify user was persisted in DB
    from sqlalchemy import select

    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.supabase_uid == FAKE_SUPABASE_UID


@pytest.mark.asyncio
async def test_signup_duplicate_email(
    async_client: AsyncClient, db_session: AsyncSession
):
    """POST /auth/signup with an existing email returns 409."""
    email = "duplicate@example.com"

    # First signup succeeds
    with patch(
        "app.services.auth_service.supabase_signup",
        new_callable=AsyncMock,
        return_value=_supabase_signup_response(email),
    ):
        resp1 = await async_client.post(
            SIGNUP_URL,
            json={"email": email, "password": "StrongP@ss1!"},
        )
    assert resp1.status_code == 201

    # Second signup with same email fails
    with patch(
        "app.services.auth_service.supabase_signup",
        new_callable=AsyncMock,
        side_effect=AppError(code=ErrorCode.RESOURCE_ALREADY_EXISTS, message="User already registered"),
    ):
        resp2 = await async_client.post(
            SIGNUP_URL,
            json={"email": email, "password": "StrongP@ss1!"},
        )

    assert resp2.status_code == 409
    body = resp2.json()
    assert body["error"]["code"] == "RESOURCE_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, db_session: AsyncSession):
    """POST /auth/login with valid credentials returns user and session."""
    email = "loginuser@example.com"
    uid = "login-uid-001"

    # Create user in DB first
    user = User(
        id=uuid.uuid4(),
        email=email,
        role=UserRole.USER,
        supabase_uid=uid,
        settings={},
    )
    db_session.add(user)
    await db_session.flush()

    with patch(
        "app.services.auth_service.supabase_login",
        new_callable=AsyncMock,
        return_value=_supabase_login_response(email, uid),
    ):
        resp = await async_client.post(
            LOGIN_URL,
            json={"email": email, "password": "StrongP@ss1!"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "user" in body
    assert "session" in body
    assert body["user"]["email"] == email


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient):
    """POST /auth/login with wrong password returns 401."""
    with patch(
        "app.services.auth_service.supabase_login",
        new_callable=AsyncMock,
        side_effect=AppError(code=ErrorCode.AUTH_INVALID_TOKEN, message="Invalid email or password"),
    ):
        resp = await async_client.post(
            LOGIN_URL,
            json={"email": "user@example.com", "password": "wrongpass"},
        )

    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.asyncio
async def test_get_me_authenticated(
    async_client: AsyncClient, test_user: User, auth_headers: dict
):
    """GET /auth/me with valid JWT returns current user."""
    resp = await async_client.get(ME_URL, headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert "user" in body
    assert body["user"]["email"] == test_user.email
    assert body["user"]["id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_get_me_unauthenticated(async_client: AsyncClient):
    """GET /auth/me without JWT returns 401."""
    resp = await async_client.get(ME_URL)

    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.asyncio
async def test_token_refresh(async_client: AsyncClient, auth_headers: dict):
    """POST /auth/refresh with valid refresh token returns new session."""
    with patch(
        "app.services.auth_service.supabase_refresh",
        new_callable=AsyncMock,
        return_value=_supabase_refresh_response(),
    ):
        resp = await async_client.post(
            REFRESH_URL,
            json={"refresh_token": FAKE_REFRESH_TOKEN},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "session" in body
    assert body["session"]["access_token"] == "new-access-token"
