import enum

from sqlalchemy import String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    USER = "user"
    SUPER_ADMIN = "super_admin"


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole), default=UserRole.USER, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # type: ignore[assignment]
    supabase_uid: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # Relationships
    profiles: Mapped[list["Profile"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Profile", back_populates="user", lazy="selectin"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "APIKey", back_populates="user", lazy="selectin"
    )
    notifications: Mapped[list["Notification"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Notification", back_populates="user"
    )
