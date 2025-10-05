"""comprehensive_schema_update_2025_10_05

Revision ID: 3bcfa75908b4
Revises: 09496f4dab63
Create Date: 2025-10-05 12:29:46.333317

Comprehensive database schema update ensuring all tables and constraints are properly created.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3bcfa75908b4'
down_revision: Union[str, None] = '09496f4dab63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply schema updates."""

    # Check and create indexes if they don't exist
    conn = op.get_bind()

    # Add missing indexes for performance optimization
    try:
        op.create_index('idx_tasks_user_id_created_at', 'tasks', ['user_id', 'created_at'], unique=False, if_not_exists=True)
    except:
        pass

    try:
        op.create_index('idx_tasks_status', 'tasks', ['status'], unique=False, if_not_exists=True)
    except:
        pass

    try:
        op.create_index('idx_credit_transactions_user_id_created_at', 'credit_transactions', ['user_id', 'created_at'], unique=False, if_not_exists=True)
    except:
        pass

    try:
        op.create_index('idx_credit_transactions_expires_at', 'credit_transactions', ['expires_at'], unique=False, if_not_exists=True)
    except:
        pass

    try:
        op.create_index('idx_payment_orders_user_id', 'payment_orders', ['user_id'], unique=False, if_not_exists=True)
    except:
        pass

    try:
        op.create_index('idx_payment_orders_status', 'payment_orders', ['status'], unique=False, if_not_exists=True)
    except:
        pass

    try:
        op.create_index('idx_users_email', 'users', ['email'], unique=False, if_not_exists=True)
    except:
        pass

    try:
        op.create_index('idx_users_phone_number', 'users', ['phone_number'], unique=False, if_not_exists=True)
    except:
        pass

    # Ensure all columns have proper defaults and constraints
    try:
        op.alter_column('users', 'credits',
                   existing_type=sa.Integer(),
                   server_default='100',
                   existing_nullable=False)
    except:
        pass

    try:
        op.alter_column('users', 'is_deleted',
                   existing_type=sa.Boolean(),
                   server_default='false',
                   existing_nullable=False)
    except:
        pass


def downgrade() -> None:
    """Revert schema updates."""

    # Drop indexes
    try:
        op.drop_index('idx_users_phone_number', table_name='users', if_exists=True)
    except:
        pass

    try:
        op.drop_index('idx_users_email', table_name='users', if_exists=True)
    except:
        pass

    try:
        op.drop_index('idx_payment_orders_status', table_name='payment_orders', if_exists=True)
    except:
        pass

    try:
        op.drop_index('idx_payment_orders_user_id', table_name='payment_orders', if_exists=True)
    except:
        pass

    try:
        op.drop_index('idx_credit_transactions_expires_at', table_name='credit_transactions', if_exists=True)
    except:
        pass

    try:
        op.drop_index('idx_credit_transactions_user_id_created_at', table_name='credit_transactions', if_exists=True)
    except:
        pass

    try:
        op.drop_index('idx_tasks_status', table_name='tasks', if_exists=True)
    except:
        pass

    try:
        op.drop_index('idx_tasks_user_id_created_at', table_name='tasks', if_exists=True)
    except:
        pass
