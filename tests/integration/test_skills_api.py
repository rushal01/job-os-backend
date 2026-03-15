"""Integration tests for Skills CRUD API — Task 1.3."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import Skill
from app.models.user import User
from tests.conftest import _make_jwt


@pytest.mark.asyncio
async def test_create_skill(
    async_client: AsyncClient, auth_headers: dict, test_user: User
):
    """POST /api/v1/skills → 201."""
    body = {
        "name": "Python",
        "category": "language",
        "proficiency": 5,
        "years_used": 8.0,
        "want_to_use": True,
    }
    resp = await async_client.post("/api/v1/skills", json=body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "Python"
    assert data["category"] == "language"
    assert data["proficiency"] == 5
    assert data["years_used"] == 8.0
    assert data["user_id"] == str(test_user.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_skills(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """GET /api/v1/skills returns user's skills."""
    skill = Skill(
        user_id=test_user.id, name="Go", category="language", proficiency=3
    )
    db_session.add(skill)
    await db_session.flush()

    resp = await async_client.get("/api/v1/skills", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all(s["user_id"] == str(test_user.id) for s in data)


@pytest.mark.asyncio
async def test_get_skill(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """GET /api/v1/skills/:id returns correct skill."""
    skill = Skill(
        user_id=test_user.id, name="Rust", category="language", proficiency=4
    )
    db_session.add(skill)
    await db_session.flush()

    resp = await async_client.get(
        f"/api/v1/skills/{skill.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Rust"


@pytest.mark.asyncio
async def test_get_skill_not_found(async_client: AsyncClient, auth_headers: dict):
    """GET /api/v1/skills/:id with non-existent UUID → 404."""
    resp = await async_client.get(
        f"/api/v1/skills/{uuid.uuid4()}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_skill(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """PUT /api/v1/skills/:id updates fields."""
    skill = Skill(
        user_id=test_user.id, name="JavaScript", category="language", proficiency=3
    )
    db_session.add(skill)
    await db_session.flush()

    resp = await async_client.put(
        f"/api/v1/skills/{skill.id}",
        json={"proficiency": 5, "years_used": 10.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["proficiency"] == 5
    assert data["years_used"] == 10.0
    assert data["name"] == "JavaScript"  # untouched


@pytest.mark.asyncio
async def test_delete_skill(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    db_session: AsyncSession,
):
    """DELETE /api/v1/skills/:id removes skill."""
    skill = Skill(
        user_id=test_user.id, name="PHP", category="language", proficiency=2
    )
    db_session.add(skill)
    await db_session.flush()

    resp = await async_client.delete(
        f"/api/v1/skills/{skill.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verify GET returns 404
    resp = await async_client.get(
        f"/api/v1/skills/{skill.id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_batch_import_skills(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
):
    """POST /api/v1/skills/batch creates multiple skills."""
    body = {
        "skills": [
            {"name": "Docker", "category": "tool", "proficiency": 4},
            {"name": "Kubernetes", "category": "tool", "proficiency": 3},
            {"name": "AWS", "category": "cloud", "proficiency": 4},
        ]
    }
    resp = await async_client.post(
        "/api/v1/skills/batch", json=body, headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert len(data) == 3
    names = {s["name"] for s in data}
    assert names == {"Docker", "Kubernetes", "AWS"}


@pytest.mark.asyncio
async def test_skill_user_isolation(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User,
):
    """User B cannot see User A's skills."""
    skill = Skill(
        user_id=test_user.id, name="Secret Skill", category="tool", proficiency=5
    )
    db_session.add(skill)

    user_b = User(
        id=uuid.uuid4(), email="skilluser@example.com", full_name="Skill User",
        supabase_uid="skill-user-uid", timezone="UTC", settings={},
    )
    db_session.add(user_b)
    await db_session.flush()

    token_b = _make_jwt(user_b.supabase_uid)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    resp = await async_client.get(
        f"/api/v1/skills/{skill.id}", headers=headers_b
    )
    assert resp.status_code == 404
