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

        if redis_client is not None:
            t0 = time.perf_counter()
            await redis_client.ping()
            latency = round((time.perf_counter() - t0) * 1000, 1)
            checks["redis"] = {"status": "healthy", "latency_ms": latency}
        else:
            checks["redis"] = {"status": "not_configured"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}

    # Check Cloudflare R2
    try:
        from app.config import settings

        if getattr(settings, "R2_ENDPOINT_URL", None) and getattr(
            settings, "R2_ACCESS_KEY_ID", None
        ):
            import boto3

            s3 = boto3.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            )
            s3.head_bucket(Bucket=settings.R2_BUCKET_NAME)
            checks["r2"] = {"status": "healthy"}
        else:
            checks["r2"] = {"status": "not_configured"}
    except Exception as e:
        checks["r2"] = {"status": "unhealthy", "error": str(e)}

    # Check Celery
    try:
        from app.tasks.celery_app import celery_app as _celery

        inspector = _celery.control.inspect()
        active = inspector.active()
        if active is not None:
            queued = sum(len(tasks) for tasks in active.values())
            checks["celery"] = {"status": "healthy", "active_tasks": queued}
        else:
            checks["celery"] = {"status": "degraded", "error": "No workers responding"}
    except Exception as e:
        checks["celery"] = {"status": "unhealthy", "error": str(e)}

    overall_status = "healthy" if all(
        c.get("status") == "healthy" for c in checks.values()
    ) else "degraded"

    return {
        "status": overall_status,
        "checks": checks,
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - _start_time),
    }
