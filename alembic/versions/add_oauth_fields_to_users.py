"""Add OAuth fields to users table

Revision ID: oauth_fields_001
Revises: 0a7e451b655c
Create Date: 2025-01-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'oauth_fields_001'
down_revision = '0a7e451b655c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add phone_number column
    op.add_column('users', sa.Column('phone_number', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_users_phone_number'), 'users', ['phone_number'], unique=True)

    # Add Google OAuth columns
    op.add_column('users', sa.Column('google_id', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)

    # Add WeChat OAuth columns
    op.add_column('users', sa.Column('wechat_openid', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_users_wechat_openid'), 'users', ['wechat_openid'], unique=True)

    op.add_column('users', sa.Column('wechat_unionid', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_users_wechat_unionid'), 'users', ['wechat_unionid'], unique=True)

    # Update auth_provider enum to include SMS
    # PostgreSQL requires special handling for enum updates
    op.execute("ALTER TYPE authprovider ADD VALUE IF NOT EXISTS 'sms'")


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_users_wechat_unionid'), table_name='users')
    op.drop_index(op.f('ix_users_wechat_openid'), table_name='users')
    op.drop_index(op.f('ix_users_google_id'), table_name='users')
    op.drop_index(op.f('ix_users_phone_number'), table_name='users')

    # Drop columns
    op.drop_column('users', 'wechat_unionid')
    op.drop_column('users', 'wechat_openid')
    op.drop_column('users', 'google_id')
    op.drop_column('users', 'phone_number')

    # Note: Cannot easily remove enum value in PostgreSQL
    # Would require recreating the enum type
