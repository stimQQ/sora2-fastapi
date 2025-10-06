"""
Payment order model.
"""

from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime
import enum
import uuid
from decimal import Decimal

from app.db.base import Base


class PaymentProvider(str, enum.Enum):
    """Payment provider types."""
    WECHAT_PAY = "wechat_pay"
    STRIPE = "stripe"


class PaymentStatus(str, enum.Enum):
    """Payment status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    PARTIAL_REFUNDED = "PARTIAL_REFUNDED"


class PaymentOrder(Base):
    """Payment order model."""

    __tablename__ = "payment_orders"

    # Primary Key
    id = Column(String(36), primary_key=True, index=True)

    # User Reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Payment Provider
    provider = Column(SQLEnum(PaymentProvider), nullable=False)
    provider_order_id = Column(String(100), unique=True, index=True, nullable=True)

    # Amount
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="USD", nullable=False)

    # Credits
    credits_purchased = Column(Integer, nullable=False)

    # Status
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)

    # Payment Details
    payment_method = Column(String(50), nullable=True)
    payment_url = Column(String(500), nullable=True)
    qr_code_url = Column(String(500), nullable=True)

    # Transaction Information
    transaction_id = Column(String(100), nullable=True, index=True)

    # Error Information
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # Return URLs
    return_url = Column(String(500), nullable=True)
    cancel_url = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<PaymentOrder(id={self.id}, amount={self.amount}, status={self.status})>"

    @property
    def is_paid(self) -> bool:
        """Check if payment is successful."""
        return self.status == PaymentStatus.SUCCEEDED