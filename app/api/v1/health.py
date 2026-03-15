import time
from typing import Any

from fastapi import APIRouter

from app.schemas.common import ErrorEnvelope

router = APIRouter()

_start_time = time.time()


@router.get(
    "/health",
    summary="Health check — dependency status",
    responses={500: {"model": ErrorEnvelope}},
)
async def health_check() -> dict[str, Any]:
    """Comprehensive health check for all dependencies."""
    checks: dict[str, Any] = {}

    # Check PostgreSQL
    try:
        from app.db.session import engine

        async with engine.connect() as conn:
            t0 = time.perf_counter()
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            latency = round((time.perf_counter() - t0) * 1000, 1)
            checks["postgres"] = {"status": "healthy", "latency_ms": latency}
    except Exception as e:
        checks["postgres"] = {"status": "unhealthy", "error": str(e)}

    # Check Redis
    try:
        from app.db.redis import redis_client

        t0 = time.perf_counter()
        await redis_client.ping()
        latency = round((time.perf_counter() - t0) * 1000, 1)
        checks["redis"] = {"status": "healthy", "latency_ms": latency}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}

    overall_status = "healthy" if all(
        c.get("status") == "healthy" for c in checks.values()
    ) else "degraded"

    return {
        "status": overall_status,
        "checks": checks,
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - _start_time),
    }
