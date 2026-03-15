"""Integration tests for Work Experience CRUD API — Task 1.3."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.work_experience import WorkExperience
from tests.conftest import _make_jwt


@pytest.mark.asyncio
async def test_create_work_experience(
    async_client: AsyncClient, auth_headers: dict, test_user: User
):
    """POST /api/v1/work-experience → 201."""
    body = {
        "company": "Anthropic",
        "title": "Senior Engineer",
        "start_date": "2023-01",
        "is_current": True,
        "location": "San Francisco, CA",
        "work_type": "hybrid",
        "description": "Building AI systems",
        "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
    }
    resp = await async_client.post(
        "/api/v1/work-experience", json=body, headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["company"] == "Anthropic"
    assert data["title"] == "Senior Engineer"
    assert data["is_current"] is True
    assert data["tech_stack"] == ["Python", "FastAPI", "PostgreSQL"]
    assert data["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_list_work_experiences(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """GET /api/v1/work-experience returns user's entries."""
    exp = WorkExperience(
        user_id=test_user.id, company="Google", title="SWE",
        start_date="2020-01", end_date="2023-01", tech_stack=[],
    )
    db_session.add(exp)
    await db_session.flush()

    resp = await async_client.get("/api/v1/work-experience", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_work_experience(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """GET /api/v1/work-experience/:id returns correct entry."""
    exp = WorkExperience(
        user_id=test_user.id, company="Meta", title="Staff Engineer",
        start_date="2019-06", tech_stack=["React"],
    )
    db_session.add(exp)
    await db_session.flush()

    resp = await async_client.get(
        f"/api/v1/work-experience/{exp.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["company"] == "Meta"


@pytest.mark.asyncio
async def test_update_work_experience(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """PUT /api/v1/work-experience/:id updates fields."""
    exp = WorkExperience(
        user_id=test_user.id, company="Startup", title="CTO",
        start_date="2018-01", tech_stack=[],
    )
    db_session.add(exp)
    await db_session.flush()

    resp = await async_client.put(
        f"/api/v1/work-experience/{exp.id}",
        json={"title": "VP Engineering", "end_date": "2023-12"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "VP Engineering"
    assert data["end_date"] == "2023-12"
    assert data["company"] == "Startup"  # untouched


@pytest.mark.asyncio
async def test_delete_work_experience(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """DELETE /api/v1/work-experience/:id removes entry."""
    exp = WorkExperience(
        user_id=test_user.id, company="Old Co", title="Intern",
        start_date="2015-06", tech_stack=[],
    )
    db_session.add(exp)
    await db_session.flush()

    resp = await async_client.delete(
        f"/api/v1/work-experience/{exp.id}", headers=auth_headers
    )
    assert resp.status_code == 200

    resp = await async_client.get(
        f"/api/v1/work-experience/{exp.id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_work_experience_user_isolation(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User,
):
    """User B cannot see User A's work experience."""
    exp = WorkExperience(
        user_id=test_user.id, company="Secret Corp", title="Agent",
        start_date="2020-01", tech_stack=[],
    )
    db_session.add(exp)

    user_b = User(
        id=uuid.uuid4(), email="expuser@example.com", full_name="Exp User",
        supabase_uid="exp-user-uid", timezone="UTC", settings={},
    )
    db_session.add(user_b)
    await db_session.flush()

    token_b = _make_jwt(user_b.supabase_uid)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    resp = await async_client.get(
        f"/api/v1/work-experience/{exp.id}", headers=headers_b
    )
    assert resp.status_code == 404
