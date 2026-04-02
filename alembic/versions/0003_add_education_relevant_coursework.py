"""Add relevant_coursework column to education table.

Revision ID: 0003_education_coursework
Revises: 0002_user_onboarding
Create Date: 2026-03-17
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0003_education_coursework"
down_revision: str | None = "0002_user_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "education",
        sa.Column("relevant_coursework", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("education", "relevant_coursework")
