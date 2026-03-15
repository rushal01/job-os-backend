import redis.asyncio as aioredis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import settings
from app.core.exceptions import AppError, ErrorCode


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Redis-based per-user rate limiting middleware.

    Uses keys: rate:{user_id}:{endpoint_group}
    Default: 100 requests per minute per user.
    TTL-based expiry (no manual cleanup needed).
    """

    PUBLIC_PATHS = {
        "/api/v1/health",
        "/api/v1/auth/signup",
        "/api/v1/auth/login",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    def __init__(self, app: object, redis: aioredis.Redis | None = None) -> None:  # type: ignore[type-arg]
        super().__init__(app)  # type: ignore[arg-type]
        self.redis = redis
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE
        self.window_seconds = 60

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for public paths
        if request.url.path in self.PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        if self.redis is None:
            return await call_next(request)

        # Extract user_id from request state (set by auth middleware/dependency)
        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            return await call_next(request)

        # Determine endpoint group from path
        path_parts = request.url.path.strip("/").split("/")
        endpoint_group = path_parts[2] if len(path_parts) > 2 else "general"

        rate_key = f"rate:{user_id}:{endpoint_group}"

        try:
            current = await self.redis.get(rate_key)
            if current is not None and int(current) >= self.rate_limit:
                ttl = await self.redis.ttl(rate_key)
                raise AppError(
                    code=ErrorCode.RATE_LIMIT_EXCEEDED,
                    message=f"Rate limit exceeded. Try again in {max(ttl, 1)} seconds.",
                    details=[{"field": "retry_after", "message": str(max(ttl, 1))}],
                )

            pipe = self.redis.pipeline()
            pipe.incr(rate_key)
            pipe.expire(rate_key, self.window_seconds)
            await pipe.execute()
        except AppError:
            raise
        except Exception as exc:
            from loguru import logger

            logger.warning(
                f"Rate limiter Redis error (allowing request through): {exc}",
                extra={"path": request.url.path},
            )

        return await call_next(request)
