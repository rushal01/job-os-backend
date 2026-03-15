import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class OutreachContact(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "outreach_contacts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # linkedin_dm, linkedin_inmail, email
    warmth: Mapped[str] = mapped_column(String(20), nullable=False)  # cold, warm, hot
    status: Mapped[str] = mapped_column(
        String(30), default="draft", nullable=False
    )  # draft, queued, sent, replied, no_response, do_not_contact

    messages: Mapped[list["OutreachMessage"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "OutreachMessage", back_populates="contact"
    )
