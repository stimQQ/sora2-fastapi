"""add_partial_refunded_to_paymentstatus_enum

Revision ID: 0bcdc0b11ebb
Revises: 8ccf99a693b5
Create Date: 2025-10-06 16:58:10.452550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bcdc0b11ebb'
down_revision: Union[str, None] = '8ccf99a693b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add PARTIAL_REFUNDED to paymentstatus enum
    # PostgreSQL requires special handling for adding enum values
    op.execute("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'PARTIAL_REFUNDED'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For safety, we'll leave the enum value in place on downgrade
    pass
