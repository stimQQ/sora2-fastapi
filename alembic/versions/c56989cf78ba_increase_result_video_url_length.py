"""increase_result_video_url_length

Revision ID: c56989cf78ba
Revises: 2e35a3c871ed
Create Date: 2025-10-04 21:21:01.675685

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c56989cf78ba'
down_revision: Union[str, None] = '2e35a3c871ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Increase result_video_url column length to accommodate longer Sora URLs with signed parameters
    op.alter_column('tasks', 'result_video_url',
                    existing_type=sa.VARCHAR(length=500),
                    type_=sa.VARCHAR(length=1000),
                    existing_nullable=True)


def downgrade() -> None:
    # Revert back to VARCHAR(500)
    op.alter_column('tasks', 'result_video_url',
                    existing_type=sa.VARCHAR(length=1000),
                    type_=sa.VARCHAR(length=500),
                    existing_nullable=True)
