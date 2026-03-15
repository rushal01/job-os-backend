"""Integration tests for Profile CRUD API — Task 1.2."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.models.user import User
from tests.conftest import _make_jwt


@pytest.mark.asyncio
async def test_create_profile(
    async_client: AsyncClient, auth_headers: dict, test_user: User
):
    """POST /api/v1/profiles → 201, all fields returned."""
    body = {
        "name": "Frontend Search",
        "target_role": "Frontend Engineer",
        "target_seniority": "Mid-level",
        "salary_min": 120000,
        "salary_max": 180000,
        "target_locations": ["New York", "Remote"],
    }
    resp = await async_client.post(
        "/api/v1/profiles", json=body, headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "Frontend Search"
    assert data["target_role"] == "Frontend Engineer"
    assert data["target_seniority"] == "Mid-level"
    assert data["salary_min"] == 120000
    assert data["salary_max"] == 180000
    assert data["target_locations"] == ["New York", "Remote"]
    assert data["user_id"] == str(test_user.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_profiles(
    async_client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    test_profile: Profile,
):
    """GET /api/v1/profiles returns only current user's profiles."""
    resp = await async_client.get("/api/v1/profiles", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1
    for p in data:
        assert p["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_get_profile(
    async_client: AsyncClient,
    auth_headers: dict,
    test_profile: Profile,
):
    """GET /api/v1/profiles/:id returns correct profile."""
    resp = await async_client.get(
        f"/api/v1/profiles/{test_profile.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == str(test_profile.id)
    assert data["name"] == "Backend Engineer Search"


@pytest.mark.asyncio
async def test_get_profile_not_found(
    async_client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/profiles/:id with non-existent UUID → 404."""
    fake_id = uuid.uuid4()
    resp = await async_client.get(
        f"/api/v1/profiles/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_profile(
    async_client: AsyncClient,
    auth_headers: dict,
    test_profile: Profile,
):
    """PUT /api/v1/profiles/:id updates fields."""
    body = {"name": "Updated Name", "salary_min": 200000}
    resp = await async_client.put(
        f"/api/v1/profiles/{test_profile.id}", json=body, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "Updated Name"
    assert data["salary_min"] == 200000
    # untouched fields preserved
    assert data["target_role"] == "Backend Engineer"


@pytest.mark.asyncio
async def test_delete_profile(
    async_client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_user: User,
):
    """DELETE sets is_deleted=true, subsequent GET → 404."""
    # Create a profile to delete
    profile = Profile(
        user_id=test_user.id,
        name="To Delete",
        target_role="Engineer",
    )
    db_session.add(profile)
    await db_session.flush()

    resp = await async_client.delete(
        f"/api/v1/profiles/{profile.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verify GET returns 404
    resp = await async_client.get(
        f"/api/v1/profiles/{profile.id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_clone_profile(
    async_client: AsyncClient,
    auth_headers: dict,
    test_profile: Profile,
):
    """POST /api/v1/profiles/:id/clone creates new profile with cloned data."""
    body = {"name": "Cloned Profile", "data_types": []}
    resp = await async_client.post(
        f"/api/v1/profiles/{test_profile.id}/clone",
        json=body,
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "Cloned Profile"
    assert data["target_role"] == test_profile.target_role
    assert data["id"] != str(test_profile.id)
    assert data["is_active"] is False  # clones start inactive


@pytest.mark.asyncio
async def test_activate_profile(
    async_client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_user: User,
):
    """PUT /api/v1/profiles/:id/activate activates target, deactivates others."""
    p1 = Profile(
        user_id=test_user.id,
        name="Profile A",
        target_role="Engineer",
        is_active=True,
    )
    p2 = Profile(
        user_id=test_user.id,
        name="Profile B",
        target_role="Manager",
        is_active=False,
    )
    db_session.add_all([p1, p2])
    await db_session.flush()

    # Activate p2
    resp = await async_client.put(
        f"/api/v1/profiles/{p2.id}/activate", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is True

    # Verify p1 is now inactive
    resp = await async_client.get(
        f"/api/v1/profiles/{p1.id}", headers=auth_headers
    )
    assert resp.json()["data"]["is_active"] is False


@pytest.mark.asyncio
async def test_completeness_calculation(
    async_client: AsyncClient,
    auth_headers: dict,
    test_user: User,
    db_session: AsyncSession,
):
    """GET /api/v1/profiles/:id/completeness returns pct + missing items."""
    # Minimal profile — only required fields
    profile = Profile(
        user_id=test_user.id,
        name="Minimal",
        target_role="Engineer",
    )
    db_session.add(profile)
    await db_session.flush()

    resp = await async_client.get(
        f"/api/v1/profiles/{profile.id}/completeness", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pct"] == 10  # only basic_info section complete
    assert "salary_expectations" in body["missing_items"]
    assert "social_links" in body["missing_items"]


@pytest.mark.asyncio
async def test_user_isolation(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_profile: Profile,
):
    """User B cannot see User A's profiles — returns 404, not 403."""
    # Create user B
    user_b = User(
        id=uuid.uuid4(),
        email="userb@example.com",
        full_name="User B",
        supabase_uid="user-b-uid",
        timezone="UTC",
        settings={},
    )
    db_session.add(user_b)
    await db_session.flush()

    token_b = _make_jwt(user_b.supabase_uid)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B tries to access User A's profile
    resp = await async_client.get(
        f"/api/v1/profiles/{test_profile.id}", headers=headers_b
    )
    assert resp.status_code == 404
