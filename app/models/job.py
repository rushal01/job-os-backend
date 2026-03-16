import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )

    # Core fields
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    ats_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    posted_date: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Salary
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    salary_estimated: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Scoring
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # auto_apply / review / skip
    decision_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Skills analysis
    skills_required: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # type: ignore[assignment]
    skills_preferred: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # type: ignore[assignment]
    skills_matched: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # type: ignore[assignment]
    skills_missing: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # type: ignore[assignment]

    # Status
    status: Mapped[str] = mapped_column(
        String(30), default="new", nullable=False
    )  # new, scored, content_ready, applied, interview, offer, rejected, skipped, bookmarked, ghosted

    # Company intel (JSONB blob)
    company_intel: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Full-text search vector
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    # Relationships
    profile = relationship("Profile", back_populates="jobs")
    applications: Mapped[list["Application"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Application", back_populates="job"
    )
    documents: Mapped[list["Document"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Document", back_populates="job"
    )
    sources: Mapped[list["JobSource"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "JobSource", back_populates="job"
    )

    __table_args__ = (
        Index("ix_jobs_user_score", "user_id", "is_deleted", text("score DESC")),
        Index("ix_jobs_user_status", "user_id", "status"),
        Index("ix_jobs_user_created", "user_id", text("created_at DESC")),
        Index("ix_jobs_search", "search_vector", postgresql_using="gin"),
    )
