"""
Payment processing API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
import logging

from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class PaymentRequest(BaseModel):
    """Payment request model."""
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="CNY", description="Currency code")
    credits: int = Field(..., gt=0, description="Number of credits to purchase")
    return_url: Optional[str] = Field(None, description="Return URL after payment")


class PaymentResponse(BaseModel):
    """Payment response model."""
    payment_id: str
    status: str
    amount: Decimal
    currency: str
    payment_url: Optional[str] = None
    qr_code: Optional[str] = None


@router.post("/wechat/create", response_model=PaymentResponse)
async def create_wechat_payment(
    request: PaymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a WeChat Pay payment.
    Returns payment URL or QR code for user to complete payment.
    """
    # TODO: Implement WeChat Pay integration
    logger.info(f"WeChat payment request: {request.amount} {request.currency} for user {current_user.get('id')}")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="WeChat Pay not yet implemented"
    )


@router.post("/stripe/create", response_model=PaymentResponse)
async def create_stripe_payment(
    request: PaymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a Stripe payment.
    Returns Stripe Checkout session URL.
    """
    # TODO: Implement Stripe integration
    logger.info(f"Stripe payment request: {request.amount} {request.currency} for user {current_user.get('id')}")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Stripe payment not yet implemented"
    )


@router.post("/webhook/wechat")
async def wechat_webhook(request: Request):
    """
    WeChat Pay webhook endpoint.
    Handles payment notifications from WeChat.
    """
    # TODO: Implement WeChat Pay webhook verification and processing
    logger.info("WeChat webhook received")

    return {"code": "SUCCESS", "message": "OK"}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Stripe webhook endpoint.
    Handles payment events from Stripe.
    """
    # TODO: Implement Stripe webhook verification and processing
    logger.info("Stripe webhook received")

    return {"received": True}


@router.get("/{payment_id}")
async def get_payment_status(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment status by ID.
    """
    # TODO: Query payment from database
    logger.info(f"Payment status request: {payment_id}")

    return {
        "payment_id": payment_id,
        "status": "pending",
        "amount": 0,
        "currency": "CNY"
    }