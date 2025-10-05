"""make_video_showcase_fields_optional

Revision ID: 31910cc5ab0a
Revises: c0b9f24f4d7b
Create Date: 2025-10-05 22:06:21.548602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31910cc5ab0a'
down_revision: Union[str, None] = 'c0b9f24f4d7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Make non-essential fields in video_showcases table nullable.
    Only id, video_url, and prompt remain required.
    """
    # Make is_active nullable
    op.alter_column('video_showcases', 'is_active',
                    existing_type=sa.Boolean(),
                    nullable=True,
                    existing_server_default=sa.text('true'))

    # Make display_order nullable
    op.alter_column('video_showcases', 'display_order',
                    existing_type=sa.Integer(),
                    nullable=True,
                    existing_server_default=sa.text('0'))

    # Make view_count nullable
    op.alter_column('video_showcases', 'view_count',
                    existing_type=sa.Integer(),
                    nullable=True,
                    existing_server_default=sa.text('0'))

    # Make created_at nullable
    op.alter_column('video_showcases', 'created_at',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=True,
                    existing_server_default=sa.text('now()'))

    # Make updated_at nullable
    op.alter_column('video_showcases', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=True,
                    existing_server_default=sa.text('now()'))


def downgrade() -> None:
    """
    Revert non-essential fields in video_showcases table to non-nullable.
    """
    # Update NULL values to defaults before making columns NOT NULL
    op.execute("UPDATE video_showcases SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE video_showcases SET display_order = 0 WHERE display_order IS NULL")
    op.execute("UPDATE video_showcases SET view_count = 0 WHERE view_count IS NULL")
    op.execute("UPDATE video_showcases SET created_at = now() WHERE created_at IS NULL")
    op.execute("UPDATE video_showcases SET updated_at = now() WHERE updated_at IS NULL")

    # Make updated_at not nullable
    op.alter_column('video_showcases', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=False,
                    existing_server_default=sa.text('now()'))

    # Make created_at not nullable
    op.alter_column('video_showcases', 'created_at',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=False,
                    existing_server_default=sa.text('now()'))

    # Make view_count not nullable
    op.alter_column('video_showcases', 'view_count',
                    existing_type=sa.Integer(),
                    nullable=False,
                    existing_server_default=sa.text('0'))

    # Make display_order not nullable
    op.alter_column('video_showcases', 'display_order',
                    existing_type=sa.Integer(),
                    nullable=False,
                    existing_server_default=sa.text('0'))

    # Make is_active not nullable
    op.alter_column('video_showcases', 'is_active',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    existing_server_default=sa.text('true'))
