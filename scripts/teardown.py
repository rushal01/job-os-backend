"""Database teardown script — truncates all tables respecting FK order.

Run: python -m scripts.teardown
"""

import asyncio

from app.db.base import Base
from app.db.session import async_session

# Ensure all models are imported so metadata is populated
from app.models import *  # noqa: F401, F403


async def teardown() -> None:
    async with async_session() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
        from loguru import logger
        logger.info("Teardown complete: all tables truncated")


if __name__ == "__main__":
    asyncio.run(teardown())
