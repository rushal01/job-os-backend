import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WorkExperience(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "work_experience"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[str] = mapped_column(String(20), nullable=False)
    end_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # remote/hybrid/onsite
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_achievement: Mapped[str | None] = mapped_column(Text, nullable=True)
    tech_stack: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # type: ignore[assignment]
