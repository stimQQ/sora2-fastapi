"""Add Sora 2 support to tasks table

Revision ID: add_sora_support
Revises: add_oauth_fields_to_users
Create Date: 2025-10-04

Changes:
- Add new task types: text-to-video, image-to-video
- Add sora_task_id column for Sora API task tracking
- Make image_url and video_url nullable (for text-to-video tasks)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_sora_support'
down_revision = 'oauth_fields_001'
branch_labels = None
depends_on = None


def upgrade():
    """Add Sora support columns to tasks table."""

    # Add sora_task_id column
    op.add_column('tasks',
        sa.Column('sora_task_id', sa.String(100), nullable=True)
    )

    # Create unique index on sora_task_id
    op.create_index('ix_tasks_sora_task_id', 'tasks', ['sora_task_id'], unique=True)

    # Make image_url and video_url nullable
    # (They are already nullable in the model, but ensure it in the database)
    op.alter_column('tasks', 'image_url',
                    existing_type=sa.String(500),
                    nullable=True)

    op.alter_column('tasks', 'video_url',
                    existing_type=sa.String(500),
                    nullable=True)

    # Note: TaskType enum values are already defined in the model
    # PostgreSQL will accept the new enum values automatically


def downgrade():
    """Remove Sora support columns from tasks table."""

    # Drop index
    op.drop_index('ix_tasks_sora_task_id', table_name='tasks')

    # Drop sora_task_id column
    op.drop_column('tasks', 'sora_task_id')

    # Revert image_url and video_url to NOT NULL
    # WARNING: This will fail if there are text-to-video tasks with NULL image_url/video_url
    op.alter_column('tasks', 'image_url',
                    existing_type=sa.String(500),
                    nullable=False)

    op.alter_column('tasks', 'video_url',
                    existing_type=sa.String(500),
                    nullable=False)
