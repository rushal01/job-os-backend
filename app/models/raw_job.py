from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RawJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "raw_jobs"

    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    dedup_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[assignment]
    normalized_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    normalized_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sources: Mapped[list["JobSource"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "JobSource", back_populates="raw_job"
    )
