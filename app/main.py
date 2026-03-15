from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.config import settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    generic_error_handler,
    validation_error_handler,
)
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    from loguru import logger

    logger.info(f"Starting Job Application OS ({settings.ENVIRONMENT})")
    yield
    logger.info("Shutting down Job Application OS")


def create_app() -> FastAPI:
    application = FastAPI(
        title="Job Application OS",
        description="AI-powered job search command center — backend API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- Exception handlers ---
    application.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(Exception, generic_error_handler)  # type: ignore[arg-type]

    # --- Middleware chain (order matters: last added = first executed) ---
    # Order 5: Route Handler (implicit)
    # Order 4: Request Logging
    application.add_middleware(RequestLoggingMiddleware)

    # Order 2: Rate Limiter (conditionally, when Redis is available)
    # Rate limiting is applied via RateLimiterMiddleware
    # Imported here to avoid circular imports when Redis is unavailable
    try:
        from app.core.rate_limiter import RateLimiterMiddleware
        from app.db.redis import redis_client

        application.add_middleware(RateLimiterMiddleware, redis=redis_client)
    except Exception:
        pass  # Skip rate limiting if Redis is unavailable

    # Order 1: CORS
    origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # --- Sentry ---
    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
            environment=settings.ENVIRONMENT,
        )

    # --- Routers ---
    application.include_router(api_v1_router)

    return application


app = create_app()
