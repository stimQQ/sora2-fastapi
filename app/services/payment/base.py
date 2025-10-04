"""
Base payment provider interface.
All payment providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum
from decimal import Decimal
from pydantic import BaseModel
from datetime import datetime


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIAL_REFUNDED = "partial_refunded"


class Currency(str, Enum):
    """Supported currencies."""
    CNY = "CNY"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    HKD = "HKD"
    SGD = "SGD"


class PaymentMethod(str, Enum):
    """Payment methods."""
    WECHAT_PAY = "wechat_pay"
    ALIPAY = "alipay"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"


class PaymentRequest(BaseModel):
    """Standard payment request."""
    order_id: str
    amount: Decimal
    currency: Currency
    description: str
    user_id: str
    metadata: Dict[str, Any] = {}
    return_url: Optional[str] = None
    notify_url: Optional[str] = None


class PaymentResponse(BaseModel):
    """Standard payment response."""
    provider: str
    transaction_id: str
    order_id: str
    amount: Decimal
    currency: Currency
    status: PaymentStatus
    payment_url: Optional[str] = None
    qr_code: Optional[str] = None
    raw_response: Dict[str, Any] = {}
    created_at: datetime
    expires_at: Optional[datetime] = None


class RefundRequest(BaseModel):
    """Refund request."""
    transaction_id: str
    amount: Optional[Decimal] = None  # None for full refund
    reason: Optional[str] = None
    notify_url: Optional[str] = None


class RefundResponse(BaseModel):
    """Refund response."""
    refund_id: str
    transaction_id: str
    amount: Decimal
    currency: Currency
    status: str
    raw_response: Dict[str, Any] = {}
    created_at: datetime


class PaymentProvider(ABC):
    """Abstract base class for payment providers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the payment provider with configuration.

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.provider_name = self.__class__.__name__.lower().replace('provider', '')

    @abstractmethod
    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Create a new payment.

        Args:
            request: Payment request details

        Returns:
            Payment response with transaction details
        """
        pass

    @abstractmethod
    async def query_payment(self, transaction_id: str) -> PaymentResponse:
        """
        Query payment status.

        Args:
            transaction_id: Transaction ID to query

        Returns:
            Current payment status and details
        """
        pass

    @abstractmethod
    async def process_webhook(self, data: Dict[str, Any], headers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Process webhook notification from payment provider.

        Args:
            data: Webhook payload
            headers: HTTP headers for signature verification

        Returns:
            Processed webhook data with standardized format
        """
        pass

    @abstractmethod
    async def refund_payment(self, request: RefundRequest) -> RefundResponse:
        """
        Refund a payment.

        Args:
            request: Refund request details

        Returns:
            Refund response
        """
        pass

    @abstractmethod
    async def cancel_payment(self, transaction_id: str) -> bool:
        """
        Cancel a pending payment.

        Args:
            transaction_id: Transaction to cancel

        Returns:
            True if successful
        """
        pass

    async def validate_webhook_signature(self, data: Any, signature: str, secret: str) -> bool:
        """
        Validate webhook signature.

        Args:
            data: Webhook data
            signature: Provided signature
            secret: Webhook secret

        Returns:
            True if signature is valid
        """
        # Default implementation, providers should override if needed
        return True

    def format_amount(self, amount: Decimal, currency: Currency) -> int:
        """
        Format amount for the payment provider.

        Args:
            amount: Amount in standard decimal format
            currency: Currency code

        Returns:
            Formatted amount (usually in cents/fen)
        """
        # Most providers use smallest currency unit
        if currency in [Currency.JPY]:
            return int(amount)  # No decimal places for JPY
        else:
            return int(amount * 100)  # Convert to cents/fen