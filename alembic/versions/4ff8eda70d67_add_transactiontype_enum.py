"""add_transactiontype_enum

Revision ID: 4ff8eda70d67
Revises: 75433d79dffb
Create Date: 2025-10-05 16:01:27.858644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4ff8eda70d67'
down_revision: Union[str, None] = '75433d79dffb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create TransactionType enum
    transaction_type_enum = postgresql.ENUM(
        'earned', 'spent', 'purchased', 'refunded', 'bonus',
        name='transactiontype',
        create_type=True
    )
    transaction_type_enum.create(op.get_bind(), checkfirst=True)

    # Alter column to use enum instead of varchar
    op.execute("ALTER TABLE credit_transactions ALTER COLUMN transaction_type TYPE transactiontype USING transaction_type::transactiontype")


def downgrade() -> None:
    # Revert column to varchar
    op.execute("ALTER TABLE credit_transactions ALTER COLUMN transaction_type TYPE VARCHAR(50)")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS transactiontype")
