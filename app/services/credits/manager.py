"""
Credit management service.
Handles all credit-related operations with atomic transactions.
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User
from app.models.credit import CreditTransaction, TransactionType
from app.models.task import Task
from app.models.payment import PaymentOrder
from app.core.config import settings

logger = logging.getLogger(__name__)


class InsufficientCreditsError(Exception):
    """Raised when user has insufficient credits."""
    pass


class CreditManager:
    """
    Manages credit operations with ACID guarantees.

    All operations are atomic and maintain consistency between
    User.credits and CreditTransaction records.
    """

    @staticmethod
    async def get_balance(
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get user's credit balance and statistics.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Dictionary with balance, earned, spent, and recent transactions
        """
        try:
            # Query user
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Get recent transactions (last 10)
            trans_stmt = (
                select(CreditTransaction)
                .where(CreditTransaction.user_id == user_id)
                .order_by(CreditTransaction.created_at.desc())
                .limit(10)
            )
            trans_result = await db.execute(trans_stmt)
            recent_transactions = trans_result.scalars().all()

            return {
                "user_id": user_id,
                "credits": user.credits,
                "total_earned": user.total_credits_earned,
                "total_spent": user.total_credits_spent,
                "recent_transactions": [
                    {
                        "id": trans.id,
                        "type": trans.transaction_type.value,
                        "amount": trans.amount,
                        "balance_after": trans.balance_after,
                        "description": trans.description,
                        "created_at": trans.created_at.isoformat()
                    }
                    for trans in recent_transactions
                ]
            }

        except Exception as e:
            logger.error(f"Failed to get credit balance for user {user_id}: {e}")
            raise

    @staticmethod
    async def deduct_credits(
        user_id: str,
        amount: int,
        reference_type: str,
        reference_id: str,
        description: str,
        db: AsyncSession,
        task_id: Optional[str] = None
    ) -> CreditTransaction:
        """
        Deduct credits from user's account atomically.

        Args:
            user_id: User ID
            amount: Amount to deduct (positive number)
            reference_type: Type of reference (e.g., "task", "purchase")
            reference_id: ID of the related entity
            description: Human-readable description
            db: Database session (must be write session)
            task_id: Optional task ID for reference

        Returns:
            Created CreditTransaction record

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            ValueError: If amount is invalid
        """
        if amount <= 0:
            raise ValueError("Deduct amount must be positive")

        try:
            # Lock user row for update to prevent race conditions
            stmt = select(User).where(User.id == user_id).with_for_update()
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Check if user has enough credits
            if user.credits < amount:
                logger.warning(
                    f"Insufficient credits for user {user_id}: "
                    f"has {user.credits}, needs {amount}"
                )
                raise InsufficientCreditsError(
                    f"Insufficient credits. You have {user.credits} credits, "
                    f"but need {amount} credits."
                )

            # Calculate new balance
            balance_before = user.credits
            new_balance = user.credits - amount

            # Update user credits
            user.credits = new_balance
            user.total_credits_spent += amount

            # Create transaction record
            transaction = CreditTransaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                transaction_type=TransactionType.SPENT,
                amount=-amount,  # Negative for spent
                balance_before=balance_before,
                balance_after=new_balance,
                reference_type=reference_type,
                reference_id=reference_id,
                description=description,
                task_id=task_id
            )

            db.add(transaction)
            await db.flush()  # Ensure transaction is created

            logger.info(
                f"Deducted {amount} credits from user {user_id}. "
                f"New balance: {new_balance}"
            )

            return transaction

        except InsufficientCreditsError:
            raise
        except Exception as e:
            logger.error(f"Failed to deduct credits: {e}")
            raise

    @staticmethod
    def calculate_video_credits(duration_seconds: float, is_pro: bool = False) -> int:
        """
        Calculate credits needed for video generation based on duration.

        Args:
            duration_seconds: Video duration in seconds
            is_pro: Whether pro version (wan-pro) is used

        Returns:
            Credits required (rounded up)
        """
        rate = settings.CREDITS_PER_SECOND_PRO if is_pro else settings.CREDITS_PER_SECOND_STANDARD
        credits = int(duration_seconds * rate)

        # Always round up to ensure sufficient credits
        if duration_seconds * rate > credits:
            credits += 1

        logger.debug(
            f"Calculated credits for {duration_seconds}s video "
            f"({'pro' if is_pro else 'standard'}): {credits} credits"
        )

        return credits

    @staticmethod
    def calculate_sora_credits(task_type: str, quality: str) -> int:
        """
        Calculate credits needed for Sora video generation.
        Sora uses fixed pricing per video, not per second.

        Args:
            task_type: Task type ('text-to-video' or 'image-to-video')
            quality: Quality level ('standard' or 'hd')

        Returns:
            Credits required (fixed amount)

        Raises:
            ValueError: If invalid task_type or quality
        """
        pricing_map = {
            "text-to-video": {
                "standard": settings.CREDITS_SORA_TEXT_TO_VIDEO_STANDARD,
                "hd": settings.CREDITS_SORA_TEXT_TO_VIDEO_HD
            },
            "image-to-video": {
                "standard": settings.CREDITS_SORA_IMAGE_TO_VIDEO_STANDARD,
                "hd": settings.CREDITS_SORA_IMAGE_TO_VIDEO_HD
            }
        }

        if task_type not in pricing_map:
            raise ValueError(
                f"Invalid Sora task type: {task_type}. "
                f"Must be 'text-to-video' or 'image-to-video'"
            )

        if quality not in pricing_map[task_type]:
            raise ValueError(
                f"Invalid quality: {quality}. Must be 'standard' or 'hd'"
            )

        credits = pricing_map[task_type][quality]

        logger.debug(
            f"Calculated credits for Sora {task_type} ({quality}): {credits} credits"
        )

        return credits

    @staticmethod
    async def refund_credits(
        user_id: str,
        amount: int,
        task_id: str,
        reason: str,
        db: AsyncSession
    ) -> CreditTransaction:
        """
        Refund credits to user's account (e.g., when a Sora task fails).

        Args:
            user_id: User ID
            amount: Amount to refund (positive number)
            task_id: Task ID that failed
            reason: Reason for refund
            db: Database session (must be write session)

        Returns:
            Created CreditTransaction record for the refund

        Raises:
            ValueError: If amount is invalid
        """
        if amount <= 0:
            raise ValueError("Refund amount must be positive")

        try:
            # Lock user row for update
            stmt = select(User).where(User.id == user_id).with_for_update()
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Calculate new balance
            balance_before = user.credits
            new_balance = user.credits + amount

            # Update user credits
            user.credits = new_balance
            # Subtract from total_credits_spent since this is a refund
            user.total_credits_spent = max(0, user.total_credits_spent - amount)

            # Calculate expiry date (6 months from now)
            expires_at = datetime.utcnow() + timedelta(days=30 * settings.CREDIT_EXPIRY_MONTHS)

            # Create refund transaction record
            transaction = CreditTransaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                transaction_type=TransactionType.REFUNDED,
                amount=amount,  # Positive for refund
                balance_before=balance_before,
                balance_after=new_balance,
                reference_type="task_refund",
                reference_id=task_id,
                description=f"Refund: {reason}",
                task_id=task_id,
                expires_at=expires_at,
                is_expired=False
            )

            db.add(transaction)
            await db.flush()

            logger.info(
                f"Refunded {amount} credits to user {user_id} for task {task_id}. "
                f"Reason: {reason}. New balance: {new_balance}"
            )

            return transaction

        except Exception as e:
            logger.error(f"Failed to refund credits: {e}", exc_info=True)
            raise

    @staticmethod
    async def add_credits(
        user_id: str,
        amount: int,
        transaction_type: TransactionType,
        reference_type: str,
        reference_id: str,
        description: str,
        db: AsyncSession,
        payment_order_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> CreditTransaction:
        """
        Add credits to user's account atomically.

        Args:
            user_id: User ID
            amount: Amount to add (positive number)
            transaction_type: Type of transaction (EARNED, PURCHASED, BONUS, REFUNDED)
            reference_type: Type of reference
            reference_id: ID of the related entity
            description: Human-readable description
            db: Database session (must be write session)
            payment_order_id: Optional payment order ID
            expires_at: Optional expiry date (defaults to 6 months from now)

        Returns:
            Created CreditTransaction record

        Raises:
            ValueError: If amount is invalid
        """
        if amount <= 0:
            raise ValueError("Add amount must be positive")

        if transaction_type not in [
            TransactionType.EARNED,
            TransactionType.PURCHASED,
            TransactionType.BONUS,
            TransactionType.REFUNDED
        ]:
            raise ValueError(f"Invalid transaction type for adding credits: {transaction_type}")

        try:
            # Lock user row for update
            stmt = select(User).where(User.id == user_id).with_for_update()
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Calculate new balance
            new_balance = user.credits + amount

            # Update user credits
            user.credits = new_balance
            user.total_credits_earned += amount

            # Calculate expiry date if not provided (6 months from now)
            if expires_at is None:
                expires_at = datetime.utcnow() + timedelta(days=30 * settings.CREDIT_EXPIRY_MONTHS)

            # Create transaction record
            transaction = CreditTransaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                transaction_type=transaction_type,
                amount=amount,  # Positive for earned
                balance_after=new_balance,
                reference_type=reference_type,
                reference_id=reference_id,
                description=description,
                payment_order_id=payment_order_id,
                expires_at=expires_at,
                is_expired=False
            )

            db.add(transaction)
            await db.flush()

            logger.info(
                f"Added {amount} credits to user {user_id} ({transaction_type.value}). "
                f"New balance: {new_balance}"
            )

            return transaction

        except Exception as e:
            logger.error(f"Failed to add credits: {e}")
            raise

    @staticmethod
    async def refund_credits_by_task(
        user_id: str,
        task_id: str,
        reason: str,
        db: AsyncSession
    ) -> Optional[CreditTransaction]:
        """
        Refund credits for a failed or cancelled task by looking up the original transaction.

        Args:
            user_id: User ID
            task_id: Task ID to refund
            reason: Reason for refund
            db: Database session (must be write session)

        Returns:
            Created CreditTransaction record, or None if no refund needed
        """
        try:
            # Find the original deduction transaction
            stmt = (
                select(CreditTransaction)
                .where(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.task_id == task_id,
                    CreditTransaction.transaction_type == TransactionType.SPENT
                )
                .order_by(CreditTransaction.created_at.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            original_transaction = result.scalar_one_or_none()

            if not original_transaction:
                logger.warning(
                    f"No deduction transaction found for task {task_id}, "
                    f"user {user_id}. Cannot refund."
                )
                return None

            # Check if already refunded
            refund_check_stmt = (
                select(CreditTransaction)
                .where(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.reference_type == "refund",
                    CreditTransaction.reference_id == original_transaction.id
                )
            )
            refund_check_result = await db.execute(refund_check_stmt)
            existing_refund = refund_check_result.scalar_one_or_none()

            if existing_refund:
                logger.info(f"Credits already refunded for transaction {original_transaction.id}")
                return existing_refund

            # Refund the credits
            refund_amount = abs(original_transaction.amount)

            transaction = await CreditManager.add_credits(
                user_id=user_id,
                amount=refund_amount,
                transaction_type=TransactionType.REFUNDED,
                reference_type="refund",
                reference_id=original_transaction.id,
                description=f"Refund for task {task_id}: {reason}",
                db=db
            )

            logger.info(
                f"Refunded {refund_amount} credits to user {user_id} "
                f"for task {task_id}"
            )

            return transaction

        except Exception as e:
            logger.error(f"Failed to refund credits: {e}")
            raise

    @staticmethod
    async def process_payment_credits(
        user_id: str,
        payment_order_id: str,
        credits_purchased: int,
        db: AsyncSession
    ) -> CreditTransaction:
        """
        Process credit purchase from payment.

        Args:
            user_id: User ID
            payment_order_id: Payment order ID
            credits_purchased: Number of credits purchased
            db: Database session (must be write session)

        Returns:
            Created CreditTransaction record
        """
        try:
            # Verify payment order exists and is paid
            stmt = select(PaymentOrder).where(PaymentOrder.id == payment_order_id)
            result = await db.execute(stmt)
            payment_order = result.scalar_one_or_none()

            if not payment_order:
                raise ValueError(f"Payment order not found: {payment_order_id}")

            if not payment_order.is_paid:
                raise ValueError(f"Payment order not paid: {payment_order_id}")

            # Check if credits already added for this payment
            check_stmt = (
                select(CreditTransaction)
                .where(CreditTransaction.payment_order_id == payment_order_id)
            )
            check_result = await db.execute(check_stmt)
            existing_transaction = check_result.scalar_one_or_none()

            if existing_transaction:
                logger.info(
                    f"Credits already processed for payment {payment_order_id}"
                )
                return existing_transaction

            # Add credits
            transaction = await CreditManager.add_credits(
                user_id=user_id,
                amount=credits_purchased,
                transaction_type=TransactionType.PURCHASED,
                reference_type="payment",
                reference_id=payment_order_id,
                description=f"Purchased {credits_purchased} credits",
                db=db,
                payment_order_id=payment_order_id
            )

            return transaction

        except Exception as e:
            logger.error(f"Failed to process payment credits: {e}")
            raise

    @staticmethod
    async def get_transaction_history(
        user_id: str,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[TransactionType] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's credit transaction history.

        Args:
            user_id: User ID
            db: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip
            transaction_type: Optional filter by transaction type

        Returns:
            List of transaction dictionaries
        """
        try:
            stmt = (
                select(CreditTransaction)
                .where(CreditTransaction.user_id == user_id)
                .order_by(CreditTransaction.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            if transaction_type:
                stmt = stmt.where(CreditTransaction.transaction_type == transaction_type)

            result = await db.execute(stmt)
            transactions = result.scalars().all()

            return [
                {
                    "id": trans.id,
                    "type": trans.transaction_type.value,
                    "amount": trans.amount,
                    "balance_after": trans.balance_after,
                    "reference_type": trans.reference_type,
                    "reference_id": trans.reference_id,
                    "description": trans.description,
                    "created_at": trans.created_at.isoformat()
                }
                for trans in transactions
            ]

        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            raise

    @staticmethod
    async def deduct_with_expiry(
        user_id: str,
        amount: int,
        reference_type: str,
        reference_id: str,
        description: str,
        db: AsyncSession,
        task_id: Optional[str] = None
    ) -> List[CreditTransaction]:
        """
        Deduct credits using FIFO (First In, First Out) logic with expiry checking.
        Uses oldest non-expired credits first.

        Args:
            user_id: User ID
            amount: Amount to deduct (positive number)
            reference_type: Type of reference (e.g., "task")
            reference_id: ID of the related entity
            description: Human-readable description
            db: Database session (must be write session)
            task_id: Optional task ID for reference

        Returns:
            List of CreditTransaction records created for deduction

        Raises:
            InsufficientCreditsError: If user doesn't have enough non-expired credits
            ValueError: If amount is invalid
        """
        if amount <= 0:
            raise ValueError("Deduct amount must be positive")

        try:
            # Lock user row for update
            stmt = select(User).where(User.id == user_id).with_for_update()
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Get available (non-expired) credits ordered by creation date (FIFO)
            now = datetime.utcnow()
            credit_stmt = (
                select(CreditTransaction)
                .where(
                    and_(
                        CreditTransaction.user_id == user_id,
                        CreditTransaction.amount > 0,  # Only positive transactions (added credits)
                        CreditTransaction.is_expired == False,
                        CreditTransaction.expires_at > now
                    )
                )
                .order_by(CreditTransaction.created_at.asc())  # FIFO: oldest first
            )
            credit_result = await db.execute(credit_stmt)
            available_credits = credit_result.scalars().all()

            # Calculate total available credits
            total_available = sum(trans.amount for trans in available_credits)

            if total_available < amount:
                logger.warning(
                    f"Insufficient non-expired credits for user {user_id}: "
                    f"has {total_available}, needs {amount}"
                )
                raise InsufficientCreditsError(
                    f"Insufficient credits. You have {total_available} available credits, "
                    f"but need {amount} credits."
                )

            # Deduct credits from user balance
            new_balance = user.credits - amount
            user.credits = new_balance
            user.total_credits_spent += amount

            # Create a single deduction transaction record
            transaction = CreditTransaction(
                id=str(uuid.uuid4()),
                user_id=user_id,
                transaction_type=TransactionType.SPENT,
                amount=-amount,  # Negative for spent
                balance_after=new_balance,
                reference_type=reference_type,
                reference_id=reference_id,
                description=description,
                task_id=task_id,
                expires_at=None,  # Spent credits don't expire
                is_expired=False
            )

            db.add(transaction)
            await db.flush()

            logger.info(
                f"Deducted {amount} credits from user {user_id} using FIFO. "
                f"New balance: {new_balance}"
            )

            return [transaction]

        except InsufficientCreditsError:
            raise
        except Exception as e:
            logger.error(f"Failed to deduct credits with expiry: {e}")
            raise

    @staticmethod
    async def expire_credits(db: AsyncSession) -> int:
        """
        Mark expired credits and update user balances.
        This should be run as a scheduled task (daily).

        Args:
            db: Database session (must be write session)

        Returns:
            Number of credits expired
        """
        try:
            now = datetime.utcnow()

            # Find all non-expired credits that have passed their expiry date
            stmt = (
                select(CreditTransaction)
                .where(
                    and_(
                        CreditTransaction.is_expired == False,
                        CreditTransaction.expires_at.isnot(None),
                        CreditTransaction.expires_at <= now,
                        CreditTransaction.amount > 0  # Only positive transactions can expire
                    )
                )
            )
            result = await db.execute(stmt)
            expired_transactions = result.scalars().all()

            if not expired_transactions:
                logger.info("No credits to expire")
                return 0

            # Group by user and calculate total expired per user
            user_expired_amounts: Dict[str, int] = {}
            for trans in expired_transactions:
                if trans.user_id not in user_expired_amounts:
                    user_expired_amounts[trans.user_id] = 0
                user_expired_amounts[trans.user_id] += trans.amount

            # Mark transactions as expired
            for trans in expired_transactions:
                trans.is_expired = True
                trans.expired_at = now

            # Update user balances
            for user_id, expired_amount in user_expired_amounts.items():
                user_stmt = select(User).where(User.id == user_id).with_for_update()
                user_result = await db.execute(user_stmt)
                user = user_result.scalar_one_or_none()

                if user:
                    # Deduct expired credits from user balance
                    user.credits = max(0, user.credits - expired_amount)
                    logger.info(
                        f"Expired {expired_amount} credits for user {user_id}. "
                        f"New balance: {user.credits}"
                    )

            await db.flush()

            total_expired = sum(user_expired_amounts.values())
            logger.info(
                f"Credit expiry completed: {total_expired} credits expired "
                f"across {len(user_expired_amounts)} users"
            )

            return total_expired

        except Exception as e:
            logger.error(f"Failed to expire credits: {e}")
            raise

    @staticmethod
    async def check_sufficient_credits(
        user_id: str,
        required_amount: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Check if user has sufficient non-expired credits.

        Args:
            user_id: User ID
            required_amount: Amount of credits required
            db: Database session

        Returns:
            Dictionary with check result and details
        """
        try:
            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Get available (non-expired) credits
            now = datetime.utcnow()
            credit_stmt = (
                select(CreditTransaction)
                .where(
                    and_(
                        CreditTransaction.user_id == user_id,
                        CreditTransaction.amount > 0,
                        CreditTransaction.is_expired == False,
                        CreditTransaction.expires_at > now
                    )
                )
            )
            credit_result = await db.execute(credit_stmt)
            available_credits = credit_result.scalars().all()

            # Calculate total available
            total_available = sum(trans.amount for trans in available_credits)

            # Also check for expiring soon (within 7 days)
            expires_soon_date = now + timedelta(days=7)
            expiring_soon = sum(
                trans.amount for trans in available_credits
                if trans.expires_at and trans.expires_at <= expires_soon_date
            )

            is_sufficient = total_available >= required_amount

            return {
                "sufficient": is_sufficient,
                "total_available": total_available,
                "required": required_amount,
                "shortfall": max(0, required_amount - total_available),
                "expiring_soon": expiring_soon,
                "user_balance": user.credits
            }

        except Exception as e:
            logger.error(f"Failed to check sufficient credits: {e}")
            raise