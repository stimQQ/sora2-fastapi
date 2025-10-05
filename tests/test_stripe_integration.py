"""
Stripe Payment Integration Tests
Tests for Stripe payment flow, webhook processing, and refunds.
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.payment.providers.stripe_provider import StripeProvider
from app.services.payment.base import (
    PaymentRequest,
    PaymentStatus,
    Currency,
    RefundRequest
)
from app.models.payment import PaymentOrder, PaymentProvider, PaymentStatus as DBPaymentStatus
from app.models.user import User
from app.models.credit import CreditTransaction, TransactionType


class TestStripeProvider:
    """Test Stripe payment provider."""

    @pytest.fixture
    def stripe_provider(self):
        """Create Stripe provider instance."""
        config = {
            "secret_key": "sk_test_xxxxxxxxxxxxx",
            "webhook_secret": "whsec_xxxxxxxxxxxxx"
        }
        return StripeProvider(config)

    @pytest.fixture
    def payment_request(self):
        """Sample payment request."""
        return PaymentRequest(
            order_id=str(uuid.uuid4()),
            amount=Decimal("100.00"),
            currency=Currency.CNY,
            description="标准包 - 1100 积分",
            user_id=str(uuid.uuid4()),
            metadata={
                "package": "standard",
                "credits": 1100
            },
            return_url="https://example.com/success"
        )

    @pytest.mark.asyncio
    async def test_create_payment(self, stripe_provider, payment_request):
        """Test creating a Stripe checkout session."""
        with patch('stripe.checkout.Session.create') as mock_create:
            # Mock Stripe response
            mock_session = Mock()
            mock_session.id = "cs_test_xxxxxxxxxxxxx"
            mock_session.url = "https://checkout.stripe.com/c/pay/cs_test_xxx"
            mock_session.payment_intent = "pi_xxxxxxxxxxxxx"
            mock_create.return_value = mock_session

            # Create payment
            response = await stripe_provider.create_payment(payment_request)

            # Verify response
            assert response.provider == "stripe"
            assert response.transaction_id == "cs_test_xxxxxxxxxxxxx"
            assert response.order_id == payment_request.order_id
            assert response.amount == Decimal("100.00")
            assert response.currency == Currency.CNY
            assert response.status == PaymentStatus.PENDING
            assert response.payment_url == "https://checkout.stripe.com/c/pay/cs_test_xxx"

            # Verify Stripe API was called correctly
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args['client_reference_id'] == payment_request.order_id
            assert call_args['metadata']['order_id'] == payment_request.order_id
            assert call_args['metadata']['user_id'] == payment_request.user_id

    @pytest.mark.asyncio
    async def test_query_payment(self, stripe_provider):
        """Test querying payment status."""
        with patch('stripe.checkout.Session.retrieve') as mock_retrieve:
            # Mock Stripe session
            mock_session = Mock()
            mock_session.id = "cs_test_xxxxxxxxxxxxx"
            mock_session.client_reference_id = "order-123"
            mock_session.amount_total = 10000  # 100.00 CNY in cents
            mock_session.currency = "cny"
            mock_session.payment_status = "paid"
            mock_session.created = 1696500000
            mock_session.to_dict.return_value = {"id": "cs_test_xxxxxxxxxxxxx"}
            mock_retrieve.return_value = mock_session

            # Query payment
            response = await stripe_provider.query_payment("cs_test_xxxxxxxxxxxxx")

            # Verify response
            assert response.provider == "stripe"
            assert response.transaction_id == "cs_test_xxxxxxxxxxxxx"
            assert response.status == PaymentStatus.SUCCEEDED
            assert response.amount == Decimal("100.00")
            assert response.currency == "CNY"

    @pytest.mark.asyncio
    async def test_process_webhook_success(self, stripe_provider):
        """Test processing successful payment webhook."""
        webhook_body = b'{"id": "evt_xxx", "type": "checkout.session.completed"}'
        headers = {"stripe-signature": "t=1234,v1=signature"}

        with patch('stripe.Webhook.construct_event') as mock_construct:
            # Mock Stripe event
            mock_event = Mock()
            mock_event.type = "checkout.session.completed"
            mock_event.data.object = Mock()
            mock_event.data.object.id = "cs_test_xxx"
            mock_event.data.object.client_reference_id = "order-123"
            mock_event.data.object.amount_total = 10000
            mock_event.data.object.currency = "cny"
            mock_event.data.object.metadata = {"package": "standard", "credits": 1100}
            mock_construct.return_value = mock_event

            # Process webhook
            result = await stripe_provider.process_webhook(webhook_body, headers)

            # Verify result
            assert result['event_type'] == "payment.succeeded"
            assert result['transaction_id'] == "cs_test_xxx"
            assert result['order_id'] == "order-123"
            assert result['amount'] == Decimal("100.00")
            assert result['status'] == PaymentStatus.SUCCEEDED

    @pytest.mark.asyncio
    async def test_refund_payment(self, stripe_provider):
        """Test refunding a payment."""
        with patch('stripe.checkout.Session.retrieve') as mock_session, \
             patch('stripe.Refund.create') as mock_refund:

            # Mock session retrieve
            mock_session.return_value = Mock(payment_intent="pi_xxxxxxxxxxxxx")

            # Mock refund
            mock_refund_obj = Mock()
            mock_refund_obj.id = "re_xxxxxxxxxxxxx"
            mock_refund_obj.amount = 10000
            mock_refund_obj.currency = "cny"
            mock_refund_obj.status = "succeeded"
            mock_refund_obj.created = 1696500000
            mock_refund_obj.to_dict.return_value = {"id": "re_xxxxxxxxxxxxx"}
            mock_refund.return_value = mock_refund_obj

            # Create refund request
            refund_request = RefundRequest(
                transaction_id="cs_test_xxxxxxxxxxxxx",
                amount=Decimal("100.00"),
                reason="Customer request"
            )

            # Process refund
            response = await stripe_provider.refund_payment(refund_request)

            # Verify response
            assert response.refund_id == "re_xxxxxxxxxxxxx"
            assert response.amount == Decimal("100.00")
            assert response.currency == "CNY"
            assert response.status == "succeeded"


class TestStripePaymentEndpoints:
    """Test Stripe payment API endpoints."""

    @pytest.fixture
    def test_user(self):
        """Create test user."""
        return {
            "id": str(uuid.uuid4()),
            "email": "test@example.com",
            "username": "testuser",
            "credits": 0
        }

    @pytest.mark.asyncio
    async def test_create_stripe_payment_endpoint(self, test_user):
        """Test POST /api/payments/stripe/create endpoint."""
        # This would be an integration test with actual database
        # For now, we test the logic flow

        from app.api.payments.router import create_stripe_payment

        # Mock request
        request = Mock()
        request.package = "standard"
        request.return_url = "https://example.com/success"

        # Mock DB session
        db = AsyncMock(spec=AsyncSession)

        with patch('app.api.payments.router.StripeProvider') as mock_provider:
            # Mock Stripe provider
            mock_instance = AsyncMock()
            mock_instance.create_payment.return_value = Mock(
                transaction_id="cs_test_xxx",
                payment_url="https://checkout.stripe.com/xxx",
                amount=Decimal("100.00"),
                currency=Currency.CNY
            )
            mock_provider.return_value = mock_instance

            # Note: Full integration test would require database setup
            # This is a simplified unit test
            pass

    @pytest.mark.asyncio
    async def test_webhook_adds_credits(self):
        """Test that successful webhook adds credits to user."""
        # This would test the complete webhook flow:
        # 1. Receive webhook
        # 2. Verify signature
        # 3. Update payment order
        # 4. Add credits to user
        # 5. Create credit transaction

        # This requires database fixtures and is better suited
        # for integration tests
        pass


class TestCreditPurchaseFlow:
    """Test complete credit purchase flow."""

    @pytest.mark.asyncio
    async def test_complete_purchase_flow(self):
        """
        Test complete flow:
        1. User creates payment
        2. Payment order created in DB
        3. Stripe session created
        4. User completes payment
        5. Webhook received
        6. Credits added to user
        """
        # This is an integration test that would require:
        # - Database setup
        # - Mock Stripe API
        # - Test user creation
        # - Complete request/response cycle

        # Example flow (pseudo-code):
        # 1. POST /api/payments/stripe/create
        # 2. Verify PaymentOrder created with status=PENDING
        # 3. Mock Stripe webhook
        # 4. POST /api/payments/webhook/stripe
        # 5. Verify PaymentOrder status=SUCCEEDED
        # 6. Verify user credits increased
        # 7. Verify CreditTransaction created

        pass


# Test data fixtures
@pytest.fixture
def mock_stripe_session():
    """Mock Stripe checkout session."""
    session = Mock()
    session.id = "cs_test_xxxxxxxxxxxxx"
    session.url = "https://checkout.stripe.com/c/pay/cs_test_xxx"
    session.payment_intent = "pi_xxxxxxxxxxxxx"
    session.client_reference_id = "order-123"
    session.amount_total = 10000
    session.currency = "cny"
    session.payment_status = "paid"
    session.created = 1696500000
    session.metadata = {"package": "standard", "credits": 1100}
    return session


@pytest.fixture
def mock_stripe_event():
    """Mock Stripe webhook event."""
    event = Mock()
    event.type = "checkout.session.completed"
    event.data.object = Mock()
    event.data.object.id = "cs_test_xxx"
    event.data.object.client_reference_id = "order-123"
    event.data.object.amount_total = 10000
    event.data.object.currency = "cny"
    event.data.object.metadata = {"package": "standard", "credits": 1100}
    return event


# Run tests with: pytest tests/test_stripe_integration.py -v
