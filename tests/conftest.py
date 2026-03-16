import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import JSON, StaticPool, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.job import Job
from app.models.profile import Profile
from app.models.user import User, UserRole

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# ---------------------------------------------------------------------------
# SQLite compatibility: remap PostgreSQL-specific column types
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR


@event.listens_for(Base.metadata, "column_reflect")
def _remap_pg_types(inspector, table, column_info):
    if isinstance(column_info["type"], (JSONB,)):
        column_info["type"] = JSON()

# Compile-time overrides so CREATE TABLE works with SQLite
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"

@compiles(TSVECTOR, "sqlite")
def _compile_tsvector_sqlite(element, compiler, **kw):
    return "TEXT"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


def _make_jwt(supabase_uid: str) -> str:
    """Create a test JWT token."""
    return jwt.encode(
        {
            "sub": supabase_uid,
            "aud": "authenticated",
            "exp": int(datetime.now(UTC).timestamp()) + 3600,
            "iat": int(datetime.now(UTC).timestamp()),
            "role": "authenticated",
        },
        settings.SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        role=UserRole.USER,
        full_name="Test User",
        supabase_uid="test-user-uid-001",
        timezone="UTC",
        settings={},
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    admin = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        role=UserRole.SUPER_ADMIN,
        full_name="Admin User",
        supabase_uid="test-admin-uid-001",
        timezone="UTC",
        settings={},
    )
    db_session.add(admin)
    await db_session.flush()
    return admin


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    token = _make_jwt(test_user.supabase_uid)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(test_admin: User) -> dict[str, str]:
    token = _make_jwt(test_admin.supabase_uid)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_profile(db_session: AsyncSession, test_user: User) -> Profile:
    profile = Profile(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Backend Engineer Search",
        target_role="Backend Engineer",
        target_seniority="Senior (6-10 YOE)",
        salary_min=150000,
        salary_max=250000,
        completeness_pct=75,
    )
    db_session.add(profile)
    await db_session.flush()
    return profile


@pytest_asyncio.fixture
async def test_job(
    db_session: AsyncSession, test_user: User, test_profile: Profile
) -> Job:
    job = Job(
        id=uuid.uuid4(),
        user_id=test_user.id,
        profile_id=test_profile.id,
        title="Senior Backend Engineer",
        company="Anthropic",
        location="San Francisco, CA",
        location_type="hybrid_flex",
        seniority="Senior",
        employment_type="Full-time",
        status="new",
        score=85.5,
        confidence=0.92,
    )
    db_session.add(job)
    await db_session.flush()
    return job
