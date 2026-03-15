import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Interview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interviews"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    round_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # phone_screen, technical, system_design, hiring_manager, final, culture_fit
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)  # zoom, meet, teams
    meeting_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    interviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interviewer_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interviewer_linkedin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    prep_pack_doc_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)  # passed, failed, pending
    difficulty_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    performance_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    questions_asked: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_steps: Mapped[str | None] = mapped_column(Text, nullable=True)

    application = relationship("Application", back_populates="interviews")
