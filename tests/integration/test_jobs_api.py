"""Integration tests for Jobs CRUD API — Task 1.4."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.profile import Profile
from app.models.user import User
from tests.conftest import _make_jwt


@pytest.mark.asyncio
async def test_create_job_manual(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    test_profile: Profile,
):
    """POST /api/v1/jobs/manual → 201."""
    body = {
        "profile_id": str(test_profile.id),
        "title": "Senior Backend Engineer",
        "company": "Anthropic",
        "location": "San Francisco",
        "location_type": "hybrid",
        "seniority": "Senior",
        "employment_type": "Full-time",
        "description": "Build AI systems",
        "salary_min": 200000,
        "salary_max": 350000,
    }
    resp = await async_client.post(
        "/api/v1/jobs/manual", json=body, headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["title"] == "Senior Backend Engineer"
    assert data["company"] == "Anthropic"
    assert data["status"] == "new"
    assert data["user_id"] == str(test_user.id)
    assert data["profile_id"] == str(test_profile.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_job(
    async_client: AsyncClient, auth_headers: dict, test_job: Job,
):
    """GET /api/v1/jobs/:id returns correct job."""
    resp = await async_client.get(
        f"/api/v1/jobs/{test_job.id}", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == str(test_job.id)
    assert data["title"] == "Senior Backend Engineer"


@pytest.mark.asyncio
async def test_get_job_not_found(async_client: AsyncClient, auth_headers: dict):
    """GET /api/v1/jobs/:id with non-existent UUID → 404."""
    resp = await async_client.get(
        f"/api/v1/jobs/{uuid.uuid4()}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs(
    async_client: AsyncClient, auth_headers: dict, test_job: Job,
):
    """GET /api/v1/jobs returns paginated results."""
    resp = await async_client.get("/api/v1/jobs", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) >= 1
    assert "has_more" in body
    assert "next_cursor" in body


@pytest.mark.asyncio
async def test_list_jobs_with_filters(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    test_profile: Profile, db_session: AsyncSession,
):
    """GET /api/v1/jobs?status=new&company=... filters correctly."""
    j1 = Job(
        user_id=test_user.id, profile_id=test_profile.id,
        title="Engineer", company="Google", status="new", score=90.0,
    )
    j2 = Job(
        user_id=test_user.id, profile_id=test_profile.id,
        title="Manager", company="Meta", status="interview", score=75.0,
    )
    db_session.add_all([j1, j2])
    await db_session.flush()

    # Filter by status
    resp = await async_client.get(
        "/api/v1/jobs?status=new", headers=auth_headers
    )
    assert resp.status_code == 200
    for job in resp.json()["data"]:
        assert job["status"] == "new"

    # Filter by company
    resp = await async_client.get(
        "/api/v1/jobs?company=Google", headers=auth_headers
    )
    assert resp.status_code == 200
    for job in resp.json()["data"]:
        assert "Google" in job["company"]


@pytest.mark.asyncio
async def test_list_jobs_pagination(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    test_profile: Profile, db_session: AsyncSession,
):
    """GET /api/v1/jobs with limit returns cursor for next page."""
    for i in range(5):
        db_session.add(Job(
            user_id=test_user.id, profile_id=test_profile.id,
            title=f"Job {i}", company=f"Company {i}", status="new",
        ))
    await db_session.flush()

    # First page
    resp = await async_client.get(
        "/api/v1/jobs?limit=3", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 3
    assert body["has_more"] is True
    assert body["next_cursor"] is not None

    # Second page
    resp = await async_client.get(
        f"/api/v1/jobs?limit=3&cursor={body['next_cursor']}", headers=auth_headers
    )
    assert resp.status_code == 200
    body2 = resp.json()
    assert len(body2["data"]) >= 1

    # No overlap between pages
    ids_page1 = {j["id"] for j in body["data"]}
    ids_page2 = {j["id"] for j in body2["data"]}
    assert ids_page1.isdisjoint(ids_page2)


@pytest.mark.asyncio
async def test_update_job_status(
    async_client: AsyncClient, auth_headers: dict, test_job: Job,
):
    """PUT /api/v1/jobs/:id/status changes status."""
    resp = await async_client.put(
        f"/api/v1/jobs/{test_job.id}/status",
        json={"status": "interview"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "interview"


@pytest.mark.asyncio
async def test_bookmark_job(
    async_client: AsyncClient, auth_headers: dict, test_job: Job,
):
    """POST /api/v1/jobs/:id/bookmark sets status to bookmarked."""
    resp = await async_client.post(
        f"/api/v1/jobs/{test_job.id}/bookmark", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "bookmarked"


@pytest.mark.asyncio
async def test_skip_job(
    async_client: AsyncClient, auth_headers: dict, test_job: Job,
):
    """POST /api/v1/jobs/:id/skip sets status to skipped."""
    resp = await async_client.post(
        f"/api/v1/jobs/{test_job.id}/skip", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_search_jobs(
    async_client: AsyncClient, auth_headers: dict, test_user: User,
    test_profile: Profile, db_session: AsyncSession,
):
    """GET /api/v1/jobs/search?q=... finds matching jobs."""
    db_session.add(Job(
        user_id=test_user.id, profile_id=test_profile.id,
        title="ML Engineer", company="OpenAI", status="new",
    ))
    db_session.add(Job(
        user_id=test_user.id, profile_id=test_profile.id,
        title="Frontend Developer", company="Stripe", status="new",
    ))
    await db_session.flush()

    resp = await async_client.get(
        "/api/v1/jobs/search?q=ML", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1
    assert any("ML" in j["title"] for j in data)


@pytest.mark.asyncio
async def test_job_user_isolation(
    async_client: AsyncClient, db_session: AsyncSession, test_user: User,
    test_job: Job,
):
    """User B cannot see User A's jobs."""
    user_b = User(
        id=uuid.uuid4(), email="jobuser@example.com", full_name="Job User",
        supabase_uid="job-user-uid", timezone="UTC", settings={},
    )
    db_session.add(user_b)
    await db_session.flush()

    token_b = _make_jwt(user_b.supabase_uid)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    resp = await async_client.get(
        f"/api/v1/jobs/{test_job.id}", headers=headers_b
    )
    assert resp.status_code == 404
