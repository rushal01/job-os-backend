"""CRUD persistence tests — verify models round-trip through SQLite test DB."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.document import Document
from app.models.job import Job
from app.models.notification import Notification
from app.models.profile import Profile
from app.models.skill import Skill
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def test_user_crud(db_session: AsyncSession, test_user: User) -> None:
    """Create, read, update a User."""
    # Read
    result = await db_session.get(User, test_user.id)
    assert result is not None
    assert result.email == "test@example.com"

    # Update
    result.full_name = "Updated Name"
    await db_session.flush()
    refreshed = await db_session.get(User, test_user.id)
    assert refreshed.full_name == "Updated Name"


async def test_profile_crud(db_session: AsyncSession, test_profile: Profile) -> None:
    """Create, read, update a Profile."""
    result = await db_session.get(Profile, test_profile.id)
    assert result is not None
    assert result.target_role == "Backend Engineer"

    result.target_role = "ML Engineer"
    await db_session.flush()
    refreshed = await db_session.get(Profile, test_profile.id)
    assert refreshed.target_role == "ML Engineer"


async def test_job_crud(db_session: AsyncSession, test_job: Job) -> None:
    """Create, read, update a Job."""
    result = await db_session.get(Job, test_job.id)
    assert result is not None
    assert result.company == "Anthropic"
    assert result.status == "new"

    result.status = "scored"
    result.score = 92.0
    await db_session.flush()
    refreshed = await db_session.get(Job, test_job.id)
    assert refreshed.status == "scored"
    assert refreshed.score == 92.0


async def test_skill_crud(db_session: AsyncSession, test_user: User) -> None:
    """Create, read, update, delete a Skill."""
    skill = Skill(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Python",
        category="language",
        proficiency=5,
        years_used=8.0,
    )
    db_session.add(skill)
    await db_session.flush()

    result = await db_session.get(Skill, skill.id)
    assert result is not None
    assert result.name == "Python"
    assert result.proficiency == 5

    # Update
    result.proficiency = 4
    await db_session.flush()
    refreshed = await db_session.get(Skill, skill.id)
    assert refreshed.proficiency == 4

    # Delete
    await db_session.delete(refreshed)
    await db_session.flush()
    gone = await db_session.get(Skill, skill.id)
    assert gone is None


async def test_application_crud(
    db_session: AsyncSession, test_user: User, test_profile: Profile, test_job: Job
) -> None:
    """Create and read an Application."""
    app = Application(
        id=uuid.uuid4(),
        job_id=test_job.id,
        user_id=test_user.id,
        profile_id=test_profile.id,
        status="pending",
        submission_method="auto",
    )
    db_session.add(app)
    await db_session.flush()

    result = await db_session.get(Application, app.id)
    assert result is not None
    assert result.status == "pending"

    result.status = "submitted"
    await db_session.flush()
    refreshed = await db_session.get(Application, app.id)
    assert refreshed.status == "submitted"


async def test_notification_crud(db_session: AsyncSession, test_user: User) -> None:
    """Create and read a Notification."""
    notif = Notification(
        id=uuid.uuid4(),
        user_id=test_user.id,
        type="job_scored",
        priority="high",
        title="New job scored 95%",
        body="A great match was found.",
        read=False,
    )
    db_session.add(notif)
    await db_session.flush()

    result = await db_session.get(Notification, notif.id)
    assert result is not None
    assert result.title == "New job scored 95%"
    assert result.read is False

    result.read = True
    await db_session.flush()
    refreshed = await db_session.get(Notification, notif.id)
    assert refreshed.read is True


async def test_document_crud(
    db_session: AsyncSession, test_user: User, test_job: Job
) -> None:
    """Create and read a Document."""
    doc = Document(
        id=uuid.uuid4(),
        user_id=test_user.id,
        job_id=test_job.id,
        type="resume_v1",
        filename="resume.pdf",
        r2_key="docs/resume.pdf",
        content_type="application/pdf",
        file_size=102400,
    )
    db_session.add(doc)
    await db_session.flush()

    result = await db_session.get(Document, doc.id)
    assert result is not None
    assert result.filename == "resume.pdf"
    assert result.file_size == 102400
