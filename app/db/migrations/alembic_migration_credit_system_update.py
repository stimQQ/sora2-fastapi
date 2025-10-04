"""
Alembic migration: Credit system update

Revision ID: 20250930_credit_system
Revises: previous_revision
Create Date: 2025-09-30

Description:
- Add expiry tracking to credit_transactions (expires_at, is_expired, expired_at)
- Add video duration tracking to tasks (output_duration_seconds, credits_calculated, credits_deducted)
- Change default user credits from 10 to 100
- Set expiry dates for existing credits retroactively
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timedelta


# revision identifiers, used by Alembic.
revision = '20250930_credit_system'
down_revision = None  # Replace with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """
    Apply migration changes.
    """
    # ========================================================================
    # 1. Update credit_transactions table
    # ========================================================================

    # Add expiry tracking columns
    op.add_column(
        'credit_transactions',
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'credit_transactions',
        sa.Column('is_expired', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column(
        'credit_transactions',
        sa.Column('expired_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Add indexes
    op.create_index(
        'idx_credit_transactions_expires_at',
        'credit_transactions',
        ['expires_at']
    )
    op.create_index(
        'idx_credit_transactions_is_expired',
        'credit_transactions',
        ['is_expired']
    )
    op.create_index(
        'idx_credit_transactions_expiry_lookup',
        'credit_transactions',
        ['user_id', 'is_expired', 'expires_at'],
        postgresql_where=sa.text('is_expired = false')
    )

    # ========================================================================
    # 2. Update tasks table
    # ========================================================================

    # Add video duration and credit tracking columns
    op.add_column(
        'tasks',
        sa.Column('output_duration_seconds', sa.Float(), nullable=True)
    )
    op.add_column(
        'tasks',
        sa.Column('credits_calculated', sa.Integer(), nullable=True)
    )
    op.add_column(
        'tasks',
        sa.Column('credits_deducted', sa.Boolean(), nullable=False, server_default='false')
    )

    # Add index
    op.create_index(
        'idx_tasks_credits_deducted',
        'tasks',
        ['credits_deducted']
    )

    # ========================================================================
    # 3. Update users table default credits
    # ========================================================================

    # Change default credits from 10 to 100
    op.alter_column(
        'users',
        'credits',
        existing_type=sa.Integer(),
        server_default='100',
        nullable=False
    )

    # ========================================================================
    # 4. Data migration: Set expiry dates for existing credits
    # ========================================================================

    # Set expiry date for existing credits (6 months from creation)
    connection = op.get_bind()

    # Update expires_at for existing credits
    connection.execute(
        sa.text("""
            UPDATE credit_transactions
            SET expires_at = created_at + INTERVAL '6 months'
            WHERE expires_at IS NULL
              AND amount > 0
              AND transaction_type IN ('earned', 'purchased', 'bonus', 'refunded')
        """)
    )

    # Mark credits that should already be expired
    connection.execute(
        sa.text("""
            UPDATE credit_transactions
            SET is_expired = TRUE,
                expired_at = NOW()
            WHERE expires_at IS NOT NULL
              AND expires_at < NOW()
              AND is_expired = FALSE
              AND amount > 0
        """)
    )

    # Recalculate user balances
    connection.execute(
        sa.text("""
            CREATE TEMP TABLE user_balance_corrections AS
            SELECT
                user_id,
                SUM(CASE
                    WHEN amount > 0 AND (is_expired = FALSE OR is_expired IS NULL) THEN amount
                    WHEN amount < 0 THEN amount
                    ELSE 0
                END) as correct_balance
            FROM credit_transactions
            GROUP BY user_id
        """)
    )

    connection.execute(
        sa.text("""
            UPDATE users u
            SET credits = GREATEST(0, ubc.correct_balance)
            FROM user_balance_corrections ubc
            WHERE u.id = ubc.user_id
        """)
    )

    connection.execute(
        sa.text("DROP TABLE user_balance_corrections")
    )


def downgrade():
    """
    Revert migration changes.
    """
    # ========================================================================
    # Revert users table
    # ========================================================================

    op.alter_column(
        'users',
        'credits',
        existing_type=sa.Integer(),
        server_default='10',
        nullable=False
    )

    # ========================================================================
    # Revert tasks table
    # ========================================================================

    op.drop_index('idx_tasks_credits_deducted', table_name='tasks')
    op.drop_column('tasks', 'credits_deducted')
    op.drop_column('tasks', 'credits_calculated')
    op.drop_column('tasks', 'output_duration_seconds')

    # ========================================================================
    # Revert credit_transactions table
    # ========================================================================

    op.drop_index('idx_credit_transactions_expiry_lookup', table_name='credit_transactions')
    op.drop_index('idx_credit_transactions_is_expired', table_name='credit_transactions')
    op.drop_index('idx_credit_transactions_expires_at', table_name='credit_transactions')

    op.drop_column('credit_transactions', 'expired_at')
    op.drop_column('credit_transactions', 'is_expired')
    op.drop_column('credit_transactions', 'expires_at')