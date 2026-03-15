import sys

from loguru import logger

from app.config import settings


def setup_logging() -> None:
    """Configure Loguru for structured JSON output."""
    logger.remove()

    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DDTHH:mm:ss.SSS}Z | {level:<8} | {module}:{function}:{line} | {message}",
        serialize=settings.ENVIRONMENT != "development",
        colorize=settings.ENVIRONMENT == "development",
        backtrace=True,
        diagnose=settings.ENVIRONMENT == "development",
    )
