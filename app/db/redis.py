import redis.asyncio as aioredis

from app.config import settings

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True,
)

redis_client = aioredis.Redis(connection_pool=redis_pool)


async def get_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    return redis_client
