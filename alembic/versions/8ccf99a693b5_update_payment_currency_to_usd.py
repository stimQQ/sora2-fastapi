"""update_payment_currency_to_usd

Revision ID: 8ccf99a693b5
Revises: c13e711b2996
Create Date: 2025-10-06 16:46:44.817015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ccf99a693b5'
down_revision: Union[str, None] = 'c13e711b2996'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update default value for currency column to USD
    op.alter_column('payment_orders', 'currency',
                    existing_type=sa.String(10),
                    server_default='USD',
                    existing_nullable=False)

    # Update existing CNY records to USD
    # Note: This changes the currency symbol but keeps the numeric amount
    # If you need to convert amounts (e.g., CNY to USD at an exchange rate),
    # you would need a more complex migration
    op.execute("UPDATE payment_orders SET currency = 'USD' WHERE currency = 'CNY'")


def downgrade() -> None:
    # Revert default value back to CNY
    op.alter_column('payment_orders', 'currency',
                    existing_type=sa.String(10),
                    server_default='CNY',
                    existing_nullable=False)

    # Revert USD records back to CNY
    op.execute("UPDATE payment_orders SET currency = 'CNY' WHERE currency = 'USD'")
