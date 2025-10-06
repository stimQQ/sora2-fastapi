"""add_succeeded_to_paymentstatus_enum

Revision ID: 023c2aeb6d50
Revises: 0bcdc0b11ebb
Create Date: 2025-10-06 17:00:34.839662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '023c2aeb6d50'
down_revision: Union[str, None] = '0bcdc0b11ebb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add SUCCEEDED to paymentstatus enum if it doesn't exist
    # The database currently has COMPLETED, but the code uses SUCCEEDED
    op.execute("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'SUCCEEDED'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # Cannot downgrade this migration
    pass
