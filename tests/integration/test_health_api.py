import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestHealthEndpoint:
    """Test /api/v1/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self) -> None:
        """Health endpoint should return 200 with status, checks, version, uptime."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/health")

        assert response.status_code == 200
        body = response.json()
        assert "status" in body
        assert "checks" in body
        assert "version" in body
        assert "uptime_seconds" in body
        assert body["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_health_no_auth_required(self) -> None:
        """Health endpoint should be accessible without authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_checks_structure(self) -> None:
        """Health checks should contain postgres and redis entries."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/health")

        body = response.json()
        assert "postgres" in body["checks"]
        assert "redis" in body["checks"]
        # In test env, these may be unhealthy, but the structure should exist
        for check_name, check_data in body["checks"].items():
            assert "status" in check_data
