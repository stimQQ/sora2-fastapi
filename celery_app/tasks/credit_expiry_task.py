"""
Credit expiry task for scheduled execution.
Expires credits that are older than 6 months.
"""

import logging
import asyncio
from datetime import datetime

from celery_app.worker import celery_app, TaskBase
from app.db.session import get_write_db_session
from app.services.credits.manager import CreditManager

logger = logging.getLogger(__name__)


@celery_app.task(base=TaskBase, name="expire_credits_daily")
def expire_credits_daily() -> dict:
    """
    Daily scheduled task to expire credits older than 6 months.

    This task:
    1. Finds all credits that have passed their expiry date
    2. Marks them as expired
    3. Deducts the expired amount from user balances

    Returns:
        Dictionary with expiry results
    """
    try:
        logger.info("Starting daily credit expiry task")

        # Run async expiry logic
        result = asyncio.run(_expire_credits_async())

        logger.info(
            f"Daily credit expiry completed successfully. "
            f"Total expired: {result['total_expired']} credits "
            f"across {result['users_affected']} users"
        )

        return result

    except Exception as e:
        logger.error(f"Daily credit expiry task failed: {e}", exc_info=True)
        raise


async def _expire_credits_async() -> dict:
    """
    Async implementation of credit expiry.

    Returns:
        Dictionary with expiry statistics
    """
    try:
        # Get database session
        async with get_write_db_session() as db:
            # Call CreditManager to expire credits
            total_expired = await CreditManager.expire_credits(db)

            # Commit the transaction
            await db.commit()

            return {
                "success": True,
                "total_expired": total_expired,
                "users_affected": 0,  # Would need to be calculated in expire_credits
                "executed_at": datetime.utcnow().isoformat(),
                "message": f"Successfully expired {total_expired} credits"
            }

    except Exception as e:
        logger.error(f"Failed to expire credits: {e}", exc_info=True)
        raise


@celery_app.task(base=TaskBase, name="check_expiring_credits")
def check_expiring_credits() -> dict:
    """
    Check for credits expiring soon (within 7 days) and send notifications.

    This can be used to notify users about credits that will expire soon.

    Returns:
        Dictionary with check results
    """
    try:
        logger.info("Checking for expiring credits")

        result = asyncio.run(_check_expiring_credits_async())

        logger.info(
            f"Expiring credits check completed. "
            f"Found {result['users_with_expiring_credits']} users with expiring credits"
        )

        return result

    except Exception as e:
        logger.error(f"Check expiring credits task failed: {e}", exc_info=True)
        raise


async def _check_expiring_credits_async() -> dict:
    """
    Async implementation of expiring credits check.

    Returns:
        Dictionary with users who have credits expiring soon
    """
    from datetime import timedelta
    from sqlalchemy import select, and_
    from app.models.credit import CreditTransaction
    from app.models.user import User

    try:
        async with get_write_db_session() as db:
            now = datetime.utcnow()
            expires_soon_date = now + timedelta(days=7)

            # Find credits expiring within 7 days
            stmt = (
                select(CreditTransaction)
                .where(
                    and_(
                        CreditTransaction.is_expired == False,
                        CreditTransaction.expires_at.isnot(None),
                        CreditTransaction.expires_at > now,
                        CreditTransaction.expires_at <= expires_soon_date,
                        CreditTransaction.amount > 0
                    )
                )
            )

            result = await db.execute(stmt)
            expiring_transactions = result.scalars().all()

            # Group by user
            users_expiring: dict[str, int] = {}
            for trans in expiring_transactions:
                if trans.user_id not in users_expiring:
                    users_expiring[trans.user_id] = 0
                users_expiring[trans.user_id] += trans.amount

            # Here you could send notifications to users
            # For now, just log the information
            for user_id, amount in users_expiring.items():
                logger.info(
                    f"User {user_id} has {amount} credits expiring within 7 days"
                )

            return {
                "success": True,
                "users_with_expiring_credits": len(users_expiring),
                "total_expiring_credits": sum(users_expiring.values()),
                "checked_at": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error(f"Failed to check expiring credits: {e}", exc_info=True)
        raise