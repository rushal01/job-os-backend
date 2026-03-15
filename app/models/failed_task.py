from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FailedTask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "failed_tasks"

    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    args: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=False)
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
