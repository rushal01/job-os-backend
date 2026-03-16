import asyncio
import socket
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# ---------------------------------------------------------------------------
# Force IPv4 DNS resolution for asyncpg connections.
#
# Supabase hostnames resolve to both IPv4 (A) and IPv6 (AAAA) records.
# Render free-tier containers have IPv4-only networking, so when asyncpg
# (via asyncio.loop.create_connection) tries the IPv6 address first the
# connection fails with "OSError: [Errno 101] Network is unreachable".
#
# We patch the event-loop's getaddrinfo to filter out IPv6 results for
# Supabase DB hosts so asyncpg always connects over IPv4.
# ---------------------------------------------------------------------------
_original_getaddrinfo = asyncio.get_event_loop_policy().__class__  # unused; we patch the loop method

_FORCE_IPV4_HOSTS: set[str] = set()
if ".supabase.co" in settings.SUPABASE_DB_URL:
    # Extract hostname from the DB URL
    from urllib.parse import urlparse

    _parsed = urlparse(settings.SUPABASE_DB_URL.replace("+asyncpg", ""))
    if _parsed.hostname:
        _FORCE_IPV4_HOSTS.add(_parsed.hostname)


def _patch_loop_for_ipv4(loop: asyncio.AbstractEventLoop) -> None:
    """Wrap loop.getaddrinfo to drop IPv6 results for Supabase hosts."""
    if getattr(loop, "_ipv4_patched", False):
        return
    original = loop.getaddrinfo

    async def _ipv4_getaddrinfo(
        host: str | None,
        port: int | str | None,
        *,
        family: int = 0,
        type: int = 0,  # noqa: A002
        proto: int = 0,
        flags: int = 0,
    ) -> list:
        if host in _FORCE_IPV4_HOSTS and family == 0:
            family = socket.AF_INET
        return await original(host, port, family=family, type=type, proto=proto, flags=flags)

    loop.getaddrinfo = _ipv4_getaddrinfo  # type: ignore[assignment]
    loop._ipv4_patched = True  # type: ignore[attr-defined]


engine = create_async_engine(
    settings.SUPABASE_DB_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
