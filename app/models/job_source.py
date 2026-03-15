import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin


class JobSource(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "job_sources"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False
    )
    raw_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_jobs.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job = relationship("Job", back_populates="sources")
    raw_job = relationship("RawJob", back_populates="sources")
