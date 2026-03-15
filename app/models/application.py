import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Application(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "applications"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="pending", nullable=False
    )  # pending, submitted, screening, interview, offer, rejected, withdrawn, ghosted
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_method: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # auto, manual, easy_apply
    submission_screenshot_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ats_debug_log: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="applications")
    profile = relationship("Profile", back_populates="applications")
    documents: Mapped[list["Document"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Document", back_populates="application"
    )
    interviews: Mapped[list["Interview"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Interview", back_populates="application"
    )

    __table_args__ = (
        Index("ix_applications_user_status", "user_id", "status", "updated_at"),
    )
