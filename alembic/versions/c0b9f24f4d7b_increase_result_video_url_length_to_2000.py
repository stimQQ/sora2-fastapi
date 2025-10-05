"""increase result_video_url length to 2000

Revision ID: c0b9f24f4d7b
Revises: e8864be53a12
Create Date: 2025-10-05 19:48:04.421360

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0b9f24f4d7b'
down_revision: Union[str, None] = 'e8864be53a12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Increase result_video_url column length from VARCHAR(1000) to VARCHAR(2000)."""
    op.alter_column('tasks', 'result_video_url',
                    type_=sa.String(2000),
                    existing_type=sa.String(1000),
                    existing_nullable=True)


def downgrade() -> None:
    """Revert result_video_url column length from VARCHAR(2000) to VARCHAR(1000)."""
    op.alter_column('tasks', 'result_video_url',
                    type_=sa.String(1000),
                    existing_type=sa.String(2000),
                    existing_nullable=True)
