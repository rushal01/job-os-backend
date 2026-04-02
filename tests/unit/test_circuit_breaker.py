from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCircuitBreaker:
    """Test Redis-based circuit breaker logic."""

    def _make_mock_redis(self) -> AsyncMock:
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.setex = AsyncMock()
        mock.delete = AsyncMock()
        mock.pipeline = MagicMock()

        pipe_mock = AsyncMock()
        pipe_mock.incr = MagicMock(return_value=pipe_mock)
        pipe_mock.expire = MagicMock(return_value=pipe_mock)
        pipe_mock.delete = MagicMock(return_value=pipe_mock)
        pipe_mock.execute = AsyncMock(return_value=[1])
        mock.pipeline.return_value = pipe_mock

        return mock

    @pytest.mark.asyncio
    async def test_circuit_starts_closed(self) -> None:
        from app.core.circuit_breaker import CircuitBreaker

        redis = self._make_mock_redis()
        cb = CircuitBreaker(redis, "test-provider")

        state = await cb.get_state()
        assert state == "closed"

    @pytest.mark.asyncio
    async def test_circuit_stays_closed_under_threshold(self) -> None:
        from app.core.circuit_breaker import CircuitBreaker

        redis = self._make_mock_redis()
        cb = CircuitBreaker(redis, "test-provider", failure_threshold=5)

        # Record 4 failures (under threshold of 5)
        pipe_mock = redis.pipeline.return_value
        pipe_mock.execute = AsyncMock(return_value=[4])

        await cb.record_failure()

        assert not await cb.is_open()

    @pytest.mark.asyncio
    async def test_circuit_opens_at_threshold(self) -> None:
        from app.core.circuit_breaker import CircuitBreaker

        redis = self._make_mock_redis()
        cb = CircuitBreaker(redis, "test-provider", failure_threshold=5)

        pipe_mock = redis.pipeline.return_value
        pipe_mock.execute = AsyncMock(return_value=[5])

        await cb.record_failure()

        # Verify setex was called to open the circuit
        redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_open_returns_true_when_open(self) -> None:
        from app.core.circuit_breaker import CircuitBreaker

        redis = self._make_mock_redis()
        redis.get = AsyncMock(return_value="1234567890")

        cb = CircuitBreaker(redis, "test-provider")
        assert await cb.is_open()

    @pytest.mark.asyncio
    async def test_record_success_resets_circuit(self) -> None:
        from app.core.circuit_breaker import CircuitBreaker

        redis = self._make_mock_redis()
        cb = CircuitBreaker(redis, "test-provider")

        await cb.record_success()

        pipe_mock = redis.pipeline.return_value
        pipe_mock.delete.assert_called()

    @pytest.mark.asyncio
    async def test_get_state_half_open(self) -> None:
        from app.core.circuit_breaker import CircuitBreaker

        redis = self._make_mock_redis()
        # Not open (no open key), but has failures
        redis.get = AsyncMock(side_effect=[None, "3"])

        cb = CircuitBreaker(redis, "test-provider")
        state = await cb.get_state()
        assert state == "half-open"
