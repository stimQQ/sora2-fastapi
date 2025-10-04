"""
Credit transaction model for tracking credit usage.
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.db.base import Base


class TransactionType(str, enum.Enum):
    """Credit transaction type."""
    EARNED = "earned"
    SPENT = "spent"
    PURCHASED = "purchased"
    REFUNDED = "refunded"
    BONUS = "bonus"


class CreditTransaction(Base):
    """Credit transaction model."""

    __tablename__ = "credit_transactions"

    # Primary Key
    id = Column(String(36), primary_key=True, index=True)

    # User Reference
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # Transaction Details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # Positive for earned/purchased, negative for spent
    balance_after = Column(Integer, nullable=False)

    # Reference
    reference_type = Column(String(50), nullable=True)  # task, payment, bonus, etc.
    reference_id = Column(String(36), nullable=True, index=True)

    # Description
    description = Column(Text, nullable=True)

    # Payment Reference (if applicable)
    payment_order_id = Column(String(36), ForeignKey("payment_orders.id"), nullable=True, index=True)

    # Task Reference (if applicable)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Expiry Tracking - Added 2025-09-30
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_expired = Column(Boolean, default=False, nullable=False, index=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<CreditTransaction(id={self.id}, type={self.transaction_type}, amount={self.amount})>"