"""Integration tests for Education CRUD API — Task 1.3."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.education import Education
from app.models.user import User
from tests.conftest import _make_jwt


@pytest.mark.asyncio
async def test_create_education(
    async_client: AsyncClient, auth_headers: dict, test_user: User
):
    """POST /api/v1/education → 201."""
    body = {
        "institution": "MIT",
        "degree": "BS",
        "field": "Computer Science",
        "start_date": "2014-09",
        "end_date": "2018-06",
        "gpa": 3.9,
        "show_gpa": True,
    }
    resp = await async_client.post(
        "/api/v1/education", json=body, headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["institution"] == "MIT"
    assert data["degree"] == "BS"
    assert data["field"] == "Computer Science"
    assert data["gpa"] == 3.9
    assert data["show_gpa"] is True
    assert data["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_list_education(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """GET /api/v1/education returns user's entries."""
    edu = Education(
        user_id=test_user.id, institution="Stanford", degree="MS",
        field="AI",
    )
    db_session.add(edu)
    await db_session.flush()

    resp = await async_client.get("/api/v1/education", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_education(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """GET /api/v1/education/:id returns correct entry."""
    edu = Education(
        user_id=test_user.id, institution="Harvard", degree="PhD",
    )
    db_session.add(edu)
    await db_session.flush()

    resp = await async_client.get(
        f"/api/v1/education/{edu.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["institution"] == "Harvard"


@pytest.mark.asyncio
async def test_update_education(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """PUT /api/v1/education/:id updates fields."""
    edu = Education(
        user_id=test_user.id, institution="Berkeley", degree="BS",
    )
    db_session.add(edu)
    await db_session.flush()

    resp = await async_client.put(
        f"/api/v1/education/{edu.id}",
        json={"degree": "MS", "field": "Data Science", "gpa": 3.8},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["degree"] == "MS"
    assert data["field"] == "Data Science"
    assert data["gpa"] == 3.8
    assert data["institution"] == "Berkeley"  # untouched


@pytest.mark.asyncio
async def test_delete_education(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """DELETE /api/v1/education/:id removes entry."""
    edu = Education(
        user_id=test_user.id, institution="Old School",
    )
    db_session.add(edu)
    await db_session.flush()

    resp = await async_client.delete(
        f"/api/v1/education/{edu.id}", headers=auth_headers
    )
    assert resp.status_code == 200

    resp = await async_client.get(
        f"/api/v1/education/{edu.id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_education_user_isolation(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User,
):
    """User B cannot see User A's education."""
    edu = Education(
        user_id=test_user.id, institution="Secret Academy",
    )
    db_session.add(edu)

    user_b = User(
        id=uuid.uuid4(), email="eduuser@example.com", full_name="Edu User",
        supabase_uid="edu-user-uid", timezone="UTC", settings={},
    )
    db_session.add(user_b)
    await db_session.flush()

    token_b = _make_jwt(user_b.supabase_uid)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    resp = await async_client.get(
        f"/api/v1/education/{edu.id}", headers=headers_b
    )
    assert resp.status_code == 404
