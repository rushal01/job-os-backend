import time

import redis.asyncio as aioredis


class CircuitBreaker:
    """Per-service circuit breaker via Redis.

    5 failures in 2 minutes → open for 60 seconds.
    States: closed (normal), open (fail fast), half-open (probe).
    """

    def __init__(
        self,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        service_name: str,
        failure_threshold: int = 5,
        failure_window: int = 120,
        recovery_timeout: int = 60,
    ) -> None:
        self.redis = redis
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.failure_window = failure_window
        self.recovery_timeout = recovery_timeout

    @property
    def _failure_key(self) -> str:
        return f"circuit:{self.service_name}:failures"

    @property
    def _open_key(self) -> str:
        return f"circuit:{self.service_name}:open"

    async def is_open(self) -> bool:
        """Check if circuit is open (fail fast)."""
        is_open = await self.redis.get(self._open_key)
        return is_open is not None

    async def record_failure(self) -> None:
        """Record a failure. Opens circuit if threshold exceeded."""
        pipe = self.redis.pipeline()
        pipe.incr(self._failure_key)
        pipe.expire(self._failure_key, self.failure_window)
        results = await pipe.execute()

        failure_count = int(results[0])
        if failure_count >= self.failure_threshold:
            await self.redis.setex(
                self._open_key, self.recovery_timeout, str(time.time())
            )

    async def record_success(self) -> None:
        """Record a success. Resets failure counter and closes circuit."""
        pipe = self.redis.pipeline()
        pipe.delete(self._failure_key)
        pipe.delete(self._open_key)
        await pipe.execute()

    async def get_state(self) -> str:
        """Get current circuit state."""
        if await self.is_open():
            return "open"
        failure_count = await self.redis.get(self._failure_key)
        if failure_count and int(failure_count) > 0:
            return "half-open"
        return "closed"
