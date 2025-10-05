"""add_missing_fields_to_credit_transactions

Revision ID: 75433d79dffb
Revises: d67b7204a2b7
Create Date: 2025-10-05 15:54:15.706407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75433d79dffb'
down_revision: Union[str, None] = 'd67b7204a2b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add payment_order_id column
    op.add_column('credit_transactions', sa.Column('payment_order_id', sa.String(length=36), nullable=True))
    op.create_foreign_key('fk_credit_transactions_payment_order_id', 'credit_transactions', 'payment_orders', ['payment_order_id'], ['id'])
    op.create_index('ix_credit_transactions_payment_order_id', 'credit_transactions', ['payment_order_id'])

    # Add task_id column
    op.add_column('credit_transactions', sa.Column('task_id', sa.String(length=36), nullable=True))
    op.create_foreign_key('fk_credit_transactions_task_id', 'credit_transactions', 'tasks', ['task_id'], ['id'])
    op.create_index('ix_credit_transactions_task_id', 'credit_transactions', ['task_id'])

    # Add expiry tracking fields
    op.add_column('credit_transactions', sa.Column('is_expired', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('ix_credit_transactions_is_expired', 'credit_transactions', ['is_expired'])

    op.add_column('credit_transactions', sa.Column('expired_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Drop columns and indexes
    op.drop_column('credit_transactions', 'expired_at')
    op.drop_index('ix_credit_transactions_is_expired', table_name='credit_transactions')
    op.drop_column('credit_transactions', 'is_expired')

    op.drop_index('ix_credit_transactions_task_id', table_name='credit_transactions')
    op.drop_constraint('fk_credit_transactions_task_id', 'credit_transactions', type_='foreignkey')
    op.drop_column('credit_transactions', 'task_id')

    op.drop_index('ix_credit_transactions_payment_order_id', table_name='credit_transactions')
    op.drop_constraint('fk_credit_transactions_payment_order_id', 'credit_transactions', type_='foreignkey')
    op.drop_column('credit_transactions', 'payment_order_id')
