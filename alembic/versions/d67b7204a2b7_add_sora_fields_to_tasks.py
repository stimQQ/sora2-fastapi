"""add_sora_fields_to_tasks

Revision ID: d67b7204a2b7
Revises: add_language_column
Create Date: 2025-10-05 15:47:59.101571

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd67b7204a2b7'
down_revision: Union[str, None] = 'add_language_column'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sora_task_id column
    op.add_column('tasks', sa.Column('sora_task_id', sa.String(length=255), nullable=True))

    # Add celery_task_id column
    op.add_column('tasks', sa.Column('celery_task_id', sa.String(length=255), nullable=True))

    # Create index on sora_task_id for faster lookups
    op.create_index('ix_tasks_sora_task_id', 'tasks', ['sora_task_id'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_tasks_sora_task_id', table_name='tasks')

    # Drop columns
    op.drop_column('tasks', 'celery_task_id')
    op.drop_column('tasks', 'sora_task_id')
