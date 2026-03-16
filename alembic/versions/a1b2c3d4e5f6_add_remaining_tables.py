"""add_remaining_tables

Revision ID: a1b2c3d4e5f6
Revises: 7a6fae2d4ef3
Create Date: 2026-03-16 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '7a6fae2d4ef3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- Recreate profiles with correct schema --
    # The initial migration had wrong column types (e.g. work_authorization
    # as String instead of JSONB, years_experience instead of years_of_experience).
    # Since this is a fresh deployment with no real data, drop and recreate.
    op.drop_table('profiles')
    op.create_table(
        'profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('target_role', sa.String(255), nullable=False),
        sa.Column('target_seniority', sa.String(100), nullable=True),
        sa.Column('target_employment_types', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('target_locations', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('negative_locations', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('years_of_experience', sa.Float, nullable=True),
        sa.Column('current_title', sa.String(255), nullable=True),
        sa.Column('salary_min', sa.Integer, nullable=True),
        sa.Column('salary_max', sa.Integer, nullable=True),
        sa.Column('salary_currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('completeness_pct', sa.Integer, nullable=False, server_default='0'),
        sa.Column('linkedin_url', sa.String(500), nullable=True),
        sa.Column('github_url', sa.String(500), nullable=True),
        sa.Column('portfolio_url', sa.String(500), nullable=True),
        sa.Column('social_urls', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('work_authorization', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('languages', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('work_preferences', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('notice_period', sa.String(100), nullable=True),
        sa.Column('availability_date', sa.String(50), nullable=True),
        sa.Column('writing_tones', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('custom_fields', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('ai_instructions', sa.Text, nullable=True),
        sa.Column('bio_snippet', sa.Text, nullable=True),
        sa.Column('scoring_weights', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('automation_config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('discovery_config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('dream_companies', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('blacklist', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- skills --
    op.create_table(
        'skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('proficiency', sa.Integer, nullable=False),
        sa.Column('years_used', sa.Float, nullable=True),
        sa.Column('last_used_date', sa.String(50), nullable=True),
        sa.Column('want_to_use', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('currently_learning', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('context', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- work_experience --
    op.create_table(
        'work_experience',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('start_date', sa.String(20), nullable=False),
        sa.Column('end_date', sa.String(20), nullable=True),
        sa.Column('is_current', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('work_type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('key_achievement', sa.Text, nullable=True),
        sa.Column('tech_stack', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- education --
    op.create_table(
        'education',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('institution', sa.String(255), nullable=False),
        sa.Column('degree', sa.String(255), nullable=True),
        sa.Column('field', sa.String(255), nullable=True),
        sa.Column('start_date', sa.String(20), nullable=True),
        sa.Column('end_date', sa.String(20), nullable=True),
        sa.Column('gpa', sa.Float, nullable=True),
        sa.Column('show_gpa', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- raw_jobs --
    op.create_table(
        'raw_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('dedup_hash', sa.String(64), nullable=False, index=True),
        sa.Column('raw_data', postgresql.JSONB, nullable=False),
        sa.Column('normalized_title', sa.String(500), nullable=True),
        sa.Column('normalized_company', sa.String(255), nullable=True),
        sa.Column('normalized_location', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- jobs --
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('location_type', sa.String(50), nullable=True),
        sa.Column('seniority', sa.String(100), nullable=True),
        sa.Column('employment_type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('apply_url', sa.String(1000), nullable=True),
        sa.Column('ats_type', sa.String(100), nullable=True),
        sa.Column('posted_date', sa.String(50), nullable=True),
        sa.Column('salary_min', sa.Integer, nullable=True),
        sa.Column('salary_max', sa.Integer, nullable=True),
        sa.Column('salary_currency', sa.String(3), nullable=True),
        sa.Column('salary_estimated', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('score', sa.Float, nullable=True),
        sa.Column('score_breakdown', postgresql.JSONB, nullable=True),
        sa.Column('confidence', sa.Float, nullable=True),
        sa.Column('risk_score', sa.Float, nullable=True),
        sa.Column('decision', sa.String(20), nullable=True),
        sa.Column('decision_reasoning', sa.Text, nullable=True),
        sa.Column('skills_required', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('skills_preferred', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('skills_matched', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('skills_missing', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('status', sa.String(30), nullable=False, server_default='new'),
        sa.Column('company_intel', postgresql.JSONB, nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR, nullable=True),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_jobs_user_score', 'jobs', ['user_id', 'is_deleted', sa.text('score DESC')])
    op.create_index('ix_jobs_user_status', 'jobs', ['user_id', 'status'])
    op.create_index('ix_jobs_user_created', 'jobs', ['user_id', sa.text('created_at DESC')])
    op.create_index('ix_jobs_search', 'jobs', ['search_vector'], postgresql_using='gin')

    # -- job_sources --
    op.create_table(
        'job_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id'), nullable=False),
        sa.Column('raw_job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('raw_jobs.id'), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('scraped_at', sa.DateTime(timezone=True), nullable=False),
    )

    # -- applications --
    op.create_table(
        'applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submission_method', sa.String(50), nullable=True),
        sa.Column('submission_screenshot_key', sa.String(500), nullable=True),
        sa.Column('ats_debug_log', postgresql.JSONB, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_applications_user_status', 'applications', ['user_id', 'status', 'updated_at'])

    # -- documents --
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id'), nullable=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('applications.id'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('r2_key', sa.String(1000), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('quality_score', sa.Integer, nullable=True),
        sa.Column('quality_breakdown', postgresql.JSONB, nullable=True),
        sa.Column('qa_report', postgresql.JSONB, nullable=True),
        sa.Column('variant_label', sa.String(50), nullable=True),
        sa.Column('template_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- review_queue --
    op.create_table(
        'review_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('item_type', sa.String(30), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id'), nullable=True),
        sa.Column('priority', sa.Integer, nullable=False, server_default='3'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reject_reason', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_review_queue_user_priority', 'review_queue', ['user_id', 'priority', 'created_at'])

    # -- outreach_contacts --
    op.create_table(
        'outreach_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('linkedin_url', sa.String(500), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('warmth', sa.String(20), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- outreach_messages --
    op.create_table(
        'outreach_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('outreach_contacts.id'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_follow_up', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('follow_up_number', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- interviews --
    op.create_table(
        'interviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('applications.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('round_type', sa.String(50), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('meeting_link', sa.String(500), nullable=True),
        sa.Column('interviewer_name', sa.String(255), nullable=True),
        sa.Column('interviewer_title', sa.String(255), nullable=True),
        sa.Column('interviewer_linkedin', sa.String(500), nullable=True),
        sa.Column('prep_pack_doc_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('outcome', sa.String(20), nullable=True),
        sa.Column('difficulty_rating', sa.Integer, nullable=True),
        sa.Column('performance_rating', sa.Integer, nullable=True),
        sa.Column('questions_asked', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('next_steps', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- notifications --
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(10), nullable=False, server_default='medium'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('body', sa.Text, nullable=True),
        sa.Column('read', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('action_url', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- activity_log --
    op.create_table(
        'activity_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('actor', sa.String(20), nullable=False, server_default='system'),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('detail', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_activity_log_user_created', 'activity_log', ['user_id', sa.text('created_at DESC')])
    op.create_index('ix_activity_log_user_action', 'activity_log', ['user_id', 'action'])

    # -- tasks --
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('task_name', sa.String(100), nullable=False),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('progress_pct', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('result', postgresql.JSONB, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- failed_tasks --
    op.create_table(
        'failed_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_name', sa.String(100), nullable=False),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('args', postgresql.JSONB, nullable=True),
        sa.Column('error', sa.Text, nullable=False),
        sa.Column('traceback', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- api_keys --
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('encrypted_key', sa.LargeBinary, nullable=False),
        sa.Column('key_nonce', sa.LargeBinary, nullable=False),
        sa.Column('key_tag', sa.LargeBinary, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('last_validated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- copilot_conversations --
    op.create_table(
        'copilot_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('messages', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('context', postgresql.JSONB, nullable=True),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    for table in [
        'copilot_conversations', 'api_keys', 'failed_tasks', 'tasks',
        'activity_log', 'notifications', 'interviews', 'outreach_messages',
        'outreach_contacts', 'review_queue', 'documents', 'applications',
        'job_sources', 'jobs', 'raw_jobs', 'education', 'work_experience', 'skills',
    ]:
        op.drop_table(table)
