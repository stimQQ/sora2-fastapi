"""
Stripe payment provider implementation.
"""

import stripe
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from app.services.payment.base import (
    PaymentProvider,
    PaymentRequest,
    PaymentResponse,
    PaymentStatus,
    RefundRequest,
    RefundResponse,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class StripeProvider(PaymentProvider):
    """Stripe payment provider."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        super().__init__(config)
        self.secret_key = config.get("secret_key") or settings.STRIPE_SECRET_KEY
        self.webhook_secret = config.get("webhook_secret") or settings.STRIPE_WEBHOOK_SECRET
        stripe.api_key = self.secret_key

    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Create a Stripe payment intent or checkout session.

        Args:
            request: Payment request details

        Returns:
            Payment response with Stripe checkout URL
        """
        try:
            # Create Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": request.currency.lower(),
                            "product_data": {
                                "name": request.description,
                            },
                            "unit_amount": self.format_amount(request.amount, request.currency),
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=request.return_url or f"{settings.FRONTEND_URL}/payment/success",
                cancel_url=request.return_url or f"{settings.FRONTEND_URL}/payment/cancel",
                client_reference_id=request.order_id,
                metadata={
                    "order_id": request.order_id,
                    "user_id": request.user_id,
                    **request.metadata,
                },
                expires_at=int((datetime.utcnow() + timedelta(hours=24)).timestamp()),
            )

            return PaymentResponse(
                provider="stripe",
                transaction_id=checkout_session.id,
                order_id=request.order_id,
                amount=request.amount,
                currency=request.currency,
                status=PaymentStatus.PENDING,
                payment_url=checkout_session.url,
                raw_response={
                    "session_id": checkout_session.id,
                    "payment_intent": checkout_session.payment_intent,
                },
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=24),
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment creation failed: {e}")
            raise Exception(f"Payment creation failed: {str(e)}")

    async def query_payment(self, transaction_id: str) -> PaymentResponse:
        """
        Query Stripe payment status.

        Args:
            transaction_id: Stripe session ID or payment intent ID

        Returns:
            Current payment status
        """
        try:
            # Try as checkout session first
            try:
                session = stripe.checkout.Session.retrieve(transaction_id)
                payment_status = self._map_stripe_status(session.payment_status)

                return PaymentResponse(
                    provider="stripe",
                    transaction_id=transaction_id,
                    order_id=session.client_reference_id,
                    amount=Decimal(session.amount_total / 100),
                    currency=session.currency.upper(),
                    status=payment_status,
                    raw_response=session.to_dict(),
                    created_at=datetime.fromtimestamp(session.created),
                )
            except:
                # Try as payment intent
                payment_intent = stripe.PaymentIntent.retrieve(transaction_id)
                payment_status = self._map_stripe_status(payment_intent.status)

                return PaymentResponse(
                    provider="stripe",
                    transaction_id=transaction_id,
                    order_id=payment_intent.metadata.get("order_id"),
                    amount=Decimal(payment_intent.amount / 100),
                    currency=payment_intent.currency.upper(),
                    status=payment_status,
                    raw_response=payment_intent.to_dict(),
                    created_at=datetime.fromtimestamp(payment_intent.created),
                )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment query failed: {e}")
            raise Exception(f"Payment query failed: {str(e)}")

    async def process_webhook(self, data: Dict[str, Any], headers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Process Stripe webhook.

        Args:
            data: Webhook payload (raw body string for Stripe)
            headers: HTTP headers including stripe-signature

        Returns:
            Processed webhook data
        """
        try:
            # Verify webhook signature
            sig_header = headers.get("stripe-signature")
            event = stripe.Webhook.construct_event(
                data, sig_header, self.webhook_secret
            )

            # Process different event types
            if event.type == "checkout.session.completed":
                session = event.data.object
                return {
                    "event_type": "payment.succeeded",
                    "transaction_id": session.id,
                    "order_id": session.client_reference_id,
                    "amount": Decimal(session.amount_total / 100),
                    "currency": session.currency.upper(),
                    "status": PaymentStatus.SUCCEEDED,
                    "metadata": session.metadata,
                }

            elif event.type == "payment_intent.succeeded":
                payment_intent = event.data.object
                return {
                    "event_type": "payment.succeeded",
                    "transaction_id": payment_intent.id,
                    "order_id": payment_intent.metadata.get("order_id"),
                    "amount": Decimal(payment_intent.amount / 100),
                    "currency": payment_intent.currency.upper(),
                    "status": PaymentStatus.SUCCEEDED,
                    "metadata": payment_intent.metadata,
                }

            elif event.type == "payment_intent.payment_failed":
                payment_intent = event.data.object
                return {
                    "event_type": "payment.failed",
                    "transaction_id": payment_intent.id,
                    "order_id": payment_intent.metadata.get("order_id"),
                    "amount": Decimal(payment_intent.amount / 100),
                    "currency": payment_intent.currency.upper(),
                    "status": PaymentStatus.FAILED,
                    "error": payment_intent.last_payment_error.message if payment_intent.last_payment_error else None,
                    "metadata": payment_intent.metadata,
                }

            else:
                logger.info(f"Unhandled Stripe event type: {event.type}")
                return {
                    "event_type": event.type,
                    "data": event.data.object,
                }

        except ValueError as e:
            logger.error(f"Invalid Stripe webhook payload: {e}")
            raise Exception("Invalid webhook payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe webhook signature: {e}")
            raise Exception("Invalid webhook signature")

    async def refund_payment(self, request: RefundRequest) -> RefundResponse:
        """
        Refund a Stripe payment.

        Args:
            request: Refund request details

        Returns:
            Refund response
        """
        try:
            # Get payment intent ID
            payment_intent_id = request.transaction_id
            if payment_intent_id.startswith("cs_"):
                # It's a checkout session, get the payment intent
                session = stripe.checkout.Session.retrieve(request.transaction_id)
                payment_intent_id = session.payment_intent

            # Create refund
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=self.format_amount(request.amount, request.currency) if request.amount and request.currency else None,
                reason=request.reason or "requested_by_customer",
            )

            return RefundResponse(
                refund_id=refund.id,
                transaction_id=request.transaction_id,
                amount=Decimal(refund.amount / 100),
                currency=refund.currency.upper(),
                status=refund.status,
                raw_response=refund.to_dict(),
                created_at=datetime.fromtimestamp(refund.created),
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund failed: {e}")
            raise Exception(f"Refund failed: {str(e)}")

    async def cancel_payment(self, transaction_id: str) -> bool:
        """
        Cancel a Stripe payment.

        Args:
            transaction_id: Transaction to cancel

        Returns:
            True if successful
        """
        try:
            # Try to cancel as payment intent
            payment_intent = stripe.PaymentIntent.cancel(transaction_id)
            return payment_intent.status == "canceled"
        except:
            try:
                # Try to expire checkout session
                stripe.checkout.Session.expire(transaction_id)
                return True
            except stripe.error.StripeError as e:
                logger.error(f"Stripe payment cancellation failed: {e}")
                return False

    def _map_stripe_status(self, stripe_status: str) -> PaymentStatus:
        """Map Stripe status to our standard status."""
        status_map = {
            "paid": PaymentStatus.SUCCEEDED,
            "unpaid": PaymentStatus.PENDING,
            "no_payment_required": PaymentStatus.SUCCEEDED,
            "requires_payment_method": PaymentStatus.PENDING,
            "requires_confirmation": PaymentStatus.PROCESSING,
            "requires_action": PaymentStatus.PROCESSING,
            "processing": PaymentStatus.PROCESSING,
            "succeeded": PaymentStatus.SUCCEEDED,
            "canceled": PaymentStatus.CANCELLED,
            "failed": PaymentStatus.FAILED,
        }
        return status_map.get(stripe_status, PaymentStatus.PENDING)