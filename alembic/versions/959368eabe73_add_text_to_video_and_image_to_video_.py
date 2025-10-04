"""add_text_to_video_and_image_to_video_enum_values

Revision ID: 959368eabe73
Revises: add_sora_support
Create Date: 2025-10-04 19:17:09.395739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '959368eabe73'
down_revision: Union[str, None] = 'add_sora_support'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new TaskType enum values to the database.

    PostgreSQL requires explicit ALTER TYPE commands to add new enum values.
    We need to add 'text-to-video' and 'image-to-video' to the tasktype enum.
    """
    # Add new enum values to the tasktype enum
    # Note: PostgreSQL doesn't support adding multiple values in one statement
    op.execute("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'text-to-video'")
    op.execute("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'image-to-video'")


def downgrade() -> None:
    """Remove new TaskType enum values from the database.

    Note: PostgreSQL doesn't support removing enum values directly.
    This would require recreating the enum type and all dependent objects.
    For safety, we'll leave the values in place during downgrade.
    """
    # PostgreSQL doesn't support removing enum values without recreating the type
    # Leaving this as a no-op for safety
    pass
