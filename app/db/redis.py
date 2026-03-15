"""Redis client — lazy-safe initialization.

If Redis is unreachable at startup, the app still starts but Redis-dependent
features (rate limiting, caching) are disabled gracefully.
"""

import redis.asyncio as aioredis
from loguru import logger

from app.config import settings

redis_client: aioredis.Redis | None = None  # type: ignore[type-arg]

try:
    redis_pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=20,
        decode_responses=True,
    )
    redis_client = aioredis.Redis(connection_pool=redis_pool)
except Exception as exc:
    logger.warning(
        f"Redis connection pool creation failed: {exc}. "
        "Redis features will be unavailable."
    )
    redis_client = None


async def get_redis() -> aioredis.Redis | None:  # type: ignore[type-arg]
    """Return the Redis client, or None if unavailable."""
    return redis_client
