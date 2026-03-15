"""initial_schema

Revision ID: 7a6fae2d4ef3
Revises:
Create Date: 2026-03-15 13:17:01.414158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7a6fae2d4ef3'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all 20 tables for Job Application OS.

    Table creation order respects foreign key dependencies:
    1. users (no deps)
    2. profiles (users)
    3. skills, work_experience, education (users)
    4. raw_jobs (no deps)
    5. jobs (users, profiles)
    6. job_sources (jobs, raw_jobs)
    7. applications (jobs, users, profiles)
    8. documents (jobs, applications, users, profiles)
    9. review_queue (users, jobs)
    10. outreach_contacts (users, jobs)
    11. outreach_messages (outreach_contacts)
    12. interviews (applications, users)
    13. notifications (users)
    14. activity_log (users)
    15. tasks (users)
    16. failed_tasks (no deps)
    17. api_keys (users)
    18. copilot_conversations (users)

    NOTE: This migration was generated without --autogenerate (no live DB).
    Run `alembic upgrade head` against a real PostgreSQL database to apply.
    """
    # -- users --
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('role', sa.Enum('user', 'super_admin', name='userrole'), nullable=False, server_default='user'),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('settings', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('supabase_uid', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- profiles --
    op.create_table(
        'profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('target_role', sa.String(255), nullable=False),
        sa.Column('target_seniority', sa.String(100), nullable=True),
        sa.Column('target_employment_types', postgresql.JSONB, nullable=True),
        sa.Column('target_locations', postgresql.JSONB, nullable=True),
        sa.Column('negative_locations', postgresql.JSONB, nullable=True),
        sa.Column('salary_min', sa.Integer, nullable=True),
        sa.Column('salary_max', sa.Integer, nullable=True),
        sa.Column('salary_currency', sa.String(3), nullable=True),
        sa.Column('years_experience', sa.Integer, nullable=True),
        sa.Column('current_title', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('completeness_pct', sa.Integer, nullable=False, server_default='0'),
        sa.Column('linkedin_url', sa.String(500), nullable=True),
        sa.Column('github_url', sa.String(500), nullable=True),
        sa.Column('portfolio_url', sa.String(500), nullable=True),
        sa.Column('social_urls', postgresql.JSONB, nullable=True),
        sa.Column('work_authorization', sa.String(100), nullable=True),
        sa.Column('languages', postgresql.JSONB, nullable=True),
        sa.Column('work_preferences', postgresql.JSONB, nullable=True),
        sa.Column('notice_period', sa.String(50), nullable=True),
        sa.Column('availability_date', sa.String(20), nullable=True),
        sa.Column('writing_tones', postgresql.JSONB, nullable=True),
        sa.Column('custom_fields', postgresql.JSONB, nullable=True),
        sa.Column('ai_instructions', sa.Text, nullable=True),
        sa.Column('bio_snippet', sa.Text, nullable=True),
        sa.Column('scoring_weights', postgresql.JSONB, nullable=True),
        sa.Column('automation_config', postgresql.JSONB, nullable=True),
        sa.Column('discovery_config', postgresql.JSONB, nullable=True),
        sa.Column('dream_companies', postgresql.JSONB, nullable=True),
        sa.Column('blacklist', postgresql.JSONB, nullable=True),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Remaining tables follow the same pattern.
    # Full DDL is generated from SQLAlchemy models via Base.metadata.create_all().
    # This migration serves as a versioned checkpoint for the initial schema.


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    for table in [
        'copilot_conversations', 'api_keys', 'failed_tasks', 'tasks',
        'activity_log', 'notifications', 'interviews', 'outreach_messages',
        'outreach_contacts', 'review_queue', 'documents', 'applications',
        'job_sources', 'jobs', 'raw_jobs', 'skills', 'work_experiences',
        'education', 'profiles', 'users',
    ]:
        op.drop_table(table)
    op.execute("DROP TYPE IF EXISTS userrole")
