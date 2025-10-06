"""
Payment processing API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import uuid
from datetime import datetime

from app.core.dependencies import get_current_user, get_db_write, get_db_read
from app.core.config import settings
from app.models.payment import PaymentOrder, PaymentProvider, PaymentStatus as DBPaymentStatus
from app.models.user import User
from app.services.payment.providers.stripe_provider import StripeProvider
from app.services.payment.base import PaymentRequest, Currency, PaymentStatus
from app.services.credits.manager import CreditManager

logger = logging.getLogger(__name__)

router = APIRouter()


class CreatePaymentRequest(BaseModel):
    """Payment creation request model."""
    package: str = Field(..., description="Credit package: trial|standard|value|premium")
    return_url: Optional[str] = Field(None, description="Return URL after payment")


class PaymentResponse(BaseModel):
    """Payment response model."""
    payment_id: str
    status: str
    amount: Decimal
    currency: str
    credits_purchased: int
    payment_url: Optional[str] = None
    qr_code: Optional[str] = None


class PackageInfo(BaseModel):
    """Credit package information."""
    name: str
    credits: int
    price: Decimal
    currency: str
    unit_price: float


@router.get("/packages")
async def get_credit_packages():
    """
    Get available credit packages.
    Returns all credit packages configured in settings.
    """
    packages = {}

    for package_id, package_data in settings.CREDIT_PACKAGES.items():
        packages[package_id] = PackageInfo(
            name=package_data["name"],
            credits=package_data["credits"],
            price=Decimal(str(package_data["price"])),
            currency="CNY",
            unit_price=package_data["unit_price"]
        )

    return {
        "packages": packages,
        "credit_value_rmb": settings.CREDIT_VALUE_RMB
    }


@router.post("/stripe/create", response_model=PaymentResponse)
async def create_stripe_payment(
    request: CreatePaymentRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_write)
):
    """
    Create a Stripe payment for credit purchase.
    Returns Stripe Checkout session URL.
    """
    try:
        # Get user_id and convert to UUID (current_user.get("id") returns string)
        if not current_user:
            logger.error("current_user is None")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        user_id_str = current_user.get("id")
        if not user_id_str:
            logger.error(f"user_id not found in current_user: {current_user}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user data"
            )

        user_id = uuid.UUID(user_id_str)

        # Validate package
        if not settings.CREDIT_PACKAGES:
            logger.error("CREDIT_PACKAGES is None or empty")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Payment packages not configured"
            )

        if request.package not in settings.CREDIT_PACKAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid package: {request.package}. Available: {list(settings.CREDIT_PACKAGES.keys())}"
            )

        package = settings.CREDIT_PACKAGES.get(request.package)
        if not package:
            logger.error(f"Package not found: {request.package}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Package not found: {request.package}"
            )

        amount = Decimal(str(package.get("price")))
        credits = package.get("credits")

        # Create payment order in database
        order_id = str(uuid.uuid4())
        payment_order = PaymentOrder(
            id=order_id,
            user_id=user_id,
            provider=PaymentProvider.STRIPE,
            amount=amount,
            currency="CNY",
            credits_purchased=credits,
            status=DBPaymentStatus.PENDING,
            return_url=request.return_url
        )

        db.add(payment_order)
        await db.commit()
        await db.refresh(payment_order)

        logger.info(f"Payment order created: {order_id} for user {user_id}, {credits} credits, ¥{amount}")

        # Create Stripe payment
        stripe_provider = StripeProvider()

        payment_request = PaymentRequest(
            order_id=order_id,
            amount=amount,
            currency=Currency.CNY,
            description=f"{package['name']} - {credits} 积分",
            user_id=str(user_id),
            metadata={
                "package": request.package,
                "credits": credits,
                "user_email": current_user.get("email", ""),
                "user_username": current_user.get("username", "")
            },
            return_url=request.return_url or f"{settings.FRONTEND_URL}/payment/success",
            notify_url=f"{settings.API_BASE_URL}/api/payments/webhook/stripe"
        )

        stripe_response = await stripe_provider.create_payment(payment_request)

        # Update payment order with Stripe session ID
        payment_order.provider_order_id = stripe_response.transaction_id
        payment_order.payment_url = stripe_response.payment_url
        await db.commit()

        logger.info(
            f"Stripe checkout created: session={stripe_response.transaction_id}, "
            f"order={order_id}, url={stripe_response.payment_url}"
        )

        return PaymentResponse(
            payment_id=order_id,
            status="pending",
            amount=amount,
            currency="CNY",
            credits_purchased=credits,
            payment_url=stripe_response.payment_url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create Stripe payment: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment creation failed: {str(e)}"
        )


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_write)
):
    """
    Stripe webhook endpoint.
    Handles payment events from Stripe.

    Important: Stripe sends raw body for signature verification.
    """
    try:
        # Get raw body for signature verification
        body = await request.body()

        # Get Stripe signature header
        sig_header = request.headers.get("stripe-signature")
        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )

        # Process webhook with Stripe provider
        stripe_provider = StripeProvider()
        webhook_data = await stripe_provider.process_webhook(
            data=body,
            headers={"stripe-signature": sig_header}
        )

        logger.info(f"Stripe webhook received: {webhook_data.get('event_type')}")

        # Handle payment succeeded
        if webhook_data.get("event_type") == "payment.succeeded":
            order_id = webhook_data.get("order_id")

            if not order_id:
                logger.warning("Webhook missing order_id")
                return {"received": True}

            # Get payment order
            stmt = select(PaymentOrder).where(PaymentOrder.id == order_id).with_for_update()
            result = await db.execute(stmt)
            payment_order = result.scalar_one_or_none()

            if not payment_order:
                logger.error(f"Payment order not found: {order_id}")
                return {"received": True}

            # Check if already processed
            if payment_order.status == DBPaymentStatus.SUCCEEDED:
                logger.info(f"Payment already processed: {order_id}")
                return {"received": True}

            # Update payment order
            payment_order.status = DBPaymentStatus.SUCCEEDED
            payment_order.transaction_id = webhook_data.get("transaction_id")
            payment_order.paid_at = datetime.utcnow()

            # Add credits to user account
            try:
                await CreditManager.process_payment_credits(
                    user_id=str(payment_order.user_id),
                    payment_order_id=order_id,
                    credits_purchased=payment_order.credits_purchased,
                    db=db
                )

                await db.commit()

                logger.info(
                    f"Payment succeeded: order={order_id}, user={payment_order.user_id}, "
                    f"credits={payment_order.credits_purchased}, amount={payment_order.amount}"
                )

            except Exception as e:
                logger.error(f"Failed to add credits for payment {order_id}: {e}")
                await db.rollback()
                raise

        # Handle payment failed
        elif webhook_data.get("event_type") == "payment.failed":
            order_id = webhook_data.get("order_id")

            if order_id:
                stmt = select(PaymentOrder).where(PaymentOrder.id == order_id)
                result = await db.execute(stmt)
                payment_order = result.scalar_one_or_none()

                if payment_order:
                    payment_order.status = DBPaymentStatus.FAILED
                    payment_order.error_message = webhook_data.get("error", "Payment failed")
                    await db.commit()

                    logger.warning(f"Payment failed: order={order_id}, error={webhook_data.get('error')}")

        return {"received": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stripe webhook processing failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.get("/{payment_id}")
async def get_payment_status(
    payment_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read)
):
    """
    Get payment status by ID.
    """
    try:
        # Convert user_id string to UUID for comparison
        user_id = uuid.UUID(current_user.get("id"))

        # Query payment order
        stmt = select(PaymentOrder).where(
            PaymentOrder.id == payment_id,
            PaymentOrder.user_id == user_id
        )
        result = await db.execute(stmt)
        payment_order = result.scalar_one_or_none()

        if not payment_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )

        # Query latest status from Stripe if pending
        if payment_order.status == DBPaymentStatus.PENDING and payment_order.provider_order_id:
            try:
                stripe_provider = StripeProvider()
                stripe_status = await stripe_provider.query_payment(payment_order.provider_order_id)

                # Update if status changed
                if stripe_status.status == PaymentStatus.SUCCEEDED and payment_order.status != DBPaymentStatus.SUCCEEDED:
                    # Trigger webhook processing manually
                    logger.info(f"Payment status changed to succeeded via query: {payment_id}")

            except Exception as e:
                logger.warning(f"Failed to query Stripe status: {e}")

        return {
            "payment_id": payment_order.id,
            "status": payment_order.status.value,
            "amount": float(payment_order.amount),
            "currency": payment_order.currency,
            "credits_purchased": payment_order.credits_purchased,
            "payment_url": payment_order.payment_url,
            "created_at": payment_order.created_at.isoformat(),
            "paid_at": payment_order.paid_at.isoformat() if payment_order.paid_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get payment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment status"
        )


@router.post("/stripe/refund")
async def refund_stripe_payment(
    payment_id: str,
    reason: Optional[str] = None,
    amount: Optional[Decimal] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_write)
):
    """
    Refund a Stripe payment (admin only or within refund window).
    """
    try:
        # Check if user is admin
        if not current_user.get("is_superuser"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can issue refunds"
            )

        # Get payment order
        stmt = select(PaymentOrder).where(PaymentOrder.id == payment_id).with_for_update()
        result = await db.execute(stmt)
        payment_order = result.scalar_one_or_none()

        if not payment_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )

        if payment_order.status != DBPaymentStatus.SUCCEEDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot refund payment with status: {payment_order.status.value}"
            )

        # Process refund with Stripe
        from app.services.payment.base import RefundRequest, Currency

        stripe_provider = StripeProvider()
        refund_request = RefundRequest(
            transaction_id=payment_order.provider_order_id,
            amount=amount,
            currency=Currency(payment_order.currency),  # Use order's currency
            reason=reason
        )

        refund_response = await stripe_provider.refund_payment(refund_request)

        # Update payment order
        payment_order.status = DBPaymentStatus.REFUNDED if not amount else DBPaymentStatus.PARTIAL_REFUNDED

        # Deduct credits from user (refund credits)
        refund_credits = payment_order.credits_purchased if not amount else int(amount / payment_order.amount * payment_order.credits_purchased)

        user_stmt = select(User).where(User.id == payment_order.user_id).with_for_update()
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if user and user.credits >= refund_credits:
            user.credits -= refund_credits
            user.total_credits_earned -= refund_credits

            # Record refund transaction
            from app.models.credit import CreditTransaction, TransactionType

            refund_transaction = CreditTransaction(
                id=str(uuid.uuid4()),
                user_id=user.id,
                transaction_type=TransactionType.REFUNDED,
                amount=-refund_credits,
                balance_after=user.credits,
                reference_type="payment_refund",
                reference_id=payment_id,
                description=f"Payment refund: {reason or 'Administrator refund'}",
                payment_order_id=payment_id
            )

            db.add(refund_transaction)

        await db.commit()

        logger.info(
            f"Payment refunded: order={payment_id}, refund_id={refund_response.refund_id}, "
            f"amount={refund_response.amount}, credits={refund_credits}"
        )

        return {
            "success": True,
            "refund_id": refund_response.refund_id,
            "amount": float(refund_response.amount),
            "credits_refunded": refund_credits,
            "message": "Refund processed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refund failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refund failed: {str(e)}"
        )


# WeChat Pay endpoints (placeholder)
@router.post("/wechat/create")
async def create_wechat_payment(
    current_user: dict = Depends(get_current_user)
):
    """
    Create a WeChat Pay payment.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="WeChat Pay not yet implemented"
    )


@router.post("/webhook/wechat")
async def wechat_webhook(request: Request):
    """
    WeChat Pay webhook endpoint.
    """
    logger.info("WeChat webhook received")
    return {"code": "SUCCESS", "message": "OK"}
