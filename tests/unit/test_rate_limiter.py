"""Unit tests for RateLimiterMiddleware (Sprint 0 scope).

4 test cases:
- test_rate_limiter_allows_under_limit
- test_rate_limiter_blocks_over_limit
- test_rate_limiter_skips_public_paths
- test_rate_limiter_skips_when_redis_unavailable
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.requests import Request
from starlette.responses import Response
from starlette.datastructures import URL, Headers

from app.core.rate_limiter import RateLimiterMiddleware
from app.core.exceptions import AppError, ErrorCode


def _make_request(path: str = "/api/v1/jobs", method: str = "GET", user_id: str | None = "user-123") -> Request:
    """Create a mock Starlette Request."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
    }
    request = Request(scope)
    if user_id is not None:
        request.state.user_id = user_id
    return request


async def _mock_call_next(request: Request) -> Response:
    """Simulate the next middleware/handler."""
    return Response(content="OK", status_code=200)


@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit():
    """Requests under the rate limit should pass through."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=b"5")  # 5 requests < 100 limit

    mock_pipe = AsyncMock()
    mock_pipe.incr = MagicMock(return_value=mock_pipe)
    mock_pipe.expire = MagicMock(return_value=mock_pipe)
    mock_pipe.execute = AsyncMock(return_value=[6, True])
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)

    middleware = RateLimiterMiddleware(app=MagicMock(), redis=mock_redis)
    request = _make_request()
    response = await middleware.dispatch(request, _mock_call_next)

    assert response.status_code == 200
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit():
    """Requests over the rate limit should raise RATE_LIMIT_EXCEEDED."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=b"100")  # At limit
    mock_redis.ttl = AsyncMock(return_value=30)

    middleware = RateLimiterMiddleware(app=MagicMock(), redis=mock_redis)
    request = _make_request()

    with pytest.raises(AppError) as exc_info:
        await middleware.dispatch(request, _mock_call_next)

    assert exc_info.value.code == ErrorCode.RATE_LIMIT_EXCEEDED
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limiter_skips_public_paths():
    """Public paths (health, signup, login) should bypass rate limiting."""
    mock_redis = AsyncMock()

    middleware = RateLimiterMiddleware(app=MagicMock(), redis=mock_redis)

    for path in ["/api/v1/health", "/api/v1/auth/signup", "/api/v1/auth/login", "/docs"]:
        request = _make_request(path=path)
        response = await middleware.dispatch(request, _mock_call_next)
        assert response.status_code == 200

    # Redis should never be called for public paths
    mock_redis.get.assert_not_called()


@pytest.mark.asyncio
async def test_rate_limiter_skips_when_redis_unavailable():
    """When Redis is None, requests should pass through without rate limiting."""
    middleware = RateLimiterMiddleware(app=MagicMock(), redis=None)
    request = _make_request()
    response = await middleware.dispatch(request, _mock_call_next)

    assert response.status_code == 200
