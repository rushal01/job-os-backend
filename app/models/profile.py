import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Profile(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    target_seniority: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_employment_types: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # type: ignore[assignment]
    target_locations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # type: ignore[assignment]
    negative_locations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # type: ignore[assignment]
    years_of_experience: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    completeness_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Deep profile fields
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    social_urls: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # type: ignore[assignment]
    work_authorization: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # type: ignore[assignment]
    languages: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # type: ignore[assignment]
    work_preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # type: ignore[assignment]
    notice_period: Mapped[str | None] = mapped_column(String(100), nullable=True)
    availability_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    writing_tones: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # type: ignore[assignment]
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # type: ignore[assignment]
    ai_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scoring & automation config (per-profile)
    scoring_weights: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # type: ignore[assignment]
    automation_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # type: ignore[assignment]
    discovery_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # type: ignore[assignment]
    dream_companies: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # type: ignore[assignment]
    blacklist: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # type: ignore[assignment]

    # Relationships
    user = relationship("User", back_populates="profiles")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="profile")  # type: ignore[name-defined]  # noqa: F821
    applications: Mapped[list["Application"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Application", back_populates="profile"
    )
