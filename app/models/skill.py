import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Skill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "skills"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # language/framework/cloud/database/tool/domain/methodology/soft_skill
    proficiency: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    years_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_used_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    want_to_use: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    currently_learning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
