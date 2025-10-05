"""Add language column to users table

Revision ID: add_language_column
Revises: 3bcfa75908b4
Create Date: 2025-01-15 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_language_column'
down_revision = '3bcfa75908b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add language column to users table."""
    # Create enum type for user language
    user_language_enum = postgresql.ENUM(
        'zh-CN', 'zh-TW', 'en', 'ja', 'ko',
        name='userlanguage',
        create_type=True
    )
    user_language_enum.create(op.get_bind(), checkfirst=True)

    # Add language column to users table
    op.add_column(
        'users',
        sa.Column(
            'language',
            user_language_enum,
            nullable=True,
            server_default='zh-CN'
        )
    )

    # Set default language based on region for existing users
    op.execute("""
        UPDATE users
        SET language = CASE
            WHEN region = 'CN' THEN 'zh-CN'::userlanguage
            WHEN region = 'US' THEN 'en'::userlanguage
            WHEN region = 'EU' THEN 'en'::userlanguage
            WHEN region = 'ASIA' THEN 'en'::userlanguage
            ELSE 'en'::userlanguage
        END
        WHERE language IS NULL
    """)


def downgrade() -> None:
    """Remove language column from users table."""
    # Drop language column
    op.drop_column('users', 'language')

    # Drop enum type
    op.execute('DROP TYPE IF EXISTS userlanguage CASCADE')
