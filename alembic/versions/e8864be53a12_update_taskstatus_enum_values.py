"""update taskstatus enum values

Revision ID: e8864be53a12
Revises: 4ff8eda70d67
Create Date: 2025-10-05 18:32:21.887392

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8864be53a12'
down_revision: Union[str, None] = '4ff8eda70d67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Update TaskStatus enum to match Python code.

    Current database values: PENDING, PROCESSING, COMPLETED, FAILED
    New values needed: PENDING, RUNNING, SUCCEEDED, FAILED, CANCELLED, TIMEOUT

    Strategy:
    1. Add new enum values using separate COMMIT after each ADD VALUE
    2. Then update existing rows to use new values

    Note: PostgreSQL requires ALTER TYPE ADD VALUE to be committed before
    the new value can be used in UPDATE statements.
    """

    # Get connection to execute raw SQL with autocommit
    connection = op.get_bind()

    # Add new enum values one by one with commit (PostgreSQL requirement)
    # We need to use raw connection with autocommit for ALTER TYPE ADD VALUE
    connection.execute(sa.text("COMMIT"))
    connection.execute(sa.text("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'RUNNING'"))
    connection.execute(sa.text("COMMIT"))
    connection.execute(sa.text("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'SUCCEEDED'"))
    connection.execute(sa.text("COMMIT"))
    connection.execute(sa.text("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'CANCELLED'"))
    connection.execute(sa.text("COMMIT"))
    connection.execute(sa.text("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'TIMEOUT'"))
    connection.execute(sa.text("COMMIT"))

    # Now we can safely update existing rows to use new values
    op.execute("UPDATE tasks SET status = 'RUNNING' WHERE status = 'PROCESSING'")
    op.execute("UPDATE tasks SET status = 'SUCCEEDED' WHERE status = 'COMPLETED'")


def downgrade() -> None:
    """
    Revert TaskStatus enum to original values.

    Note: PostgreSQL doesn't support removing enum values directly.
    We can only rename back.
    """
    # Revert data
    op.execute("UPDATE tasks SET status = 'PROCESSING' WHERE status = 'RUNNING'")
    op.execute("UPDATE tasks SET status = 'COMPLETED' WHERE status = 'SUCCEEDED'")

    # Note: Cannot remove enum values in PostgreSQL without recreating the type
    # This downgrade only reverts the data, not the enum type itself
