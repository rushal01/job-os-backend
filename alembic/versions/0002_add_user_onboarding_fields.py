"""Add has_completed_onboarding and last_login_at to users table.

Revision ID: 0002_user_onboarding
Revises: 0001_initial_schema
Create Date: 2026-03-16
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0002_user_onboarding"
down_revision: str | None = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "has_completed_onboarding",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "has_completed_onboarding")
