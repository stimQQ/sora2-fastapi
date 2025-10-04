"""add_lowercase_hyphenated_animate_enum_values

Revision ID: 2e35a3c871ed
Revises: 959368eabe73
Create Date: 2025-10-04 19:18:40.558875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e35a3c871ed'
down_revision: Union[str, None] = '959368eabe73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add lowercase hyphenated enum values for existing task types.

    The initial migration created UPPERCASE enum values (ANIMATE_MOVE, ANIMATE_MIX)
    but the Python model uses lowercase hyphenated values (animate-move, animate-mix).
    This migration adds the correct lowercase versions to match the model.
    """
    # Add lowercase hyphenated versions of the original enum values
    op.execute("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'animate-move'")
    op.execute("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'animate-mix'")


def downgrade() -> None:
    """Remove lowercase hyphenated enum values.

    Note: PostgreSQL doesn't support removing enum values without recreating the type.
    This is a no-op for safety.
    """
    # PostgreSQL doesn't support removing enum values
    pass
