"""
User model for authentication and user management.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.db.base import Base


class AuthProvider(str, enum.Enum):
    """Authentication provider types."""
    EMAIL = "email"
    SMS = "sms"
    WECHAT = "wechat"
    GOOGLE = "google"


class UserRegion(str, enum.Enum):
    """User region."""
    CN = "CN"
    US = "US"
    EU = "EU"
    ASIA = "ASIA"


class User(Base):
    """User model."""

    __tablename__ = "users"

    # Primary Key
    id = Column(String(36), primary_key=True, index=True)

    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    auth_provider = Column(SQLEnum(AuthProvider), default=AuthProvider.EMAIL)
    provider_user_id = Column(String(255), nullable=True, index=True)

    # OAuth fields
    google_id = Column(String(255), unique=True, index=True, nullable=True)
    wechat_openid = Column(String(255), unique=True, index=True, nullable=True)
    wechat_unionid = Column(String(255), unique=True, index=True, nullable=True)

    # Profile
    username = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    region = Column(SQLEnum(UserRegion), default=UserRegion.CN)

    # Credits - Updated 2025-09-30
    credits = Column(Integer, default=100, nullable=False)  # Changed from 10 to 100
    total_credits_earned = Column(Integer, default=0, nullable=False)
    total_credits_spent = Column(Integer, default=0, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, provider={self.auth_provider})>"

    @property
    def is_deleted(self) -> bool:
        """Check if user is soft deleted."""
        return self.deleted_at is not None