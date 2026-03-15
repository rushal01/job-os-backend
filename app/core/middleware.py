import time
import uuid

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs each request with unique request_id, user_id, method, path, status, and duration."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()

        user_id = getattr(request.state, "user_id", None)

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.bind(
            request_id=request_id,
            user_id=str(user_id) if user_id else None,
        ).info(
            f"{request.method} {request.url.path} → {response.status_code} ({duration_ms}ms)"
        )

        response.headers["X-Request-ID"] = request_id
        return response
