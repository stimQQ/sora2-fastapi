"""
Notification tasks for sending webhooks and emails.
"""

import logging
import httpx
from typing import Dict, Any, Optional
import asyncio

from celery_app.worker import celery_app, TaskBase
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(base=TaskBase, bind=True, name="send_webhook")
def send_webhook(
    self,
    webhook_url: str,
    payload: Dict[str, Any],
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send webhook notification to user-provided URL.

    Args:
        webhook_url: Webhook destination URL
        payload: Webhook payload
        task_id: Optional task ID for logging

    Returns:
        Result with status and response
    """
    try:
        logger.info(f"Sending webhook to {webhook_url} for task {task_id}")

        # Run async function in sync context
        result = asyncio.run(_send_webhook_async(webhook_url, payload))

        return result

    except Exception as e:
        logger.error(f"Webhook failed for task {task_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60, max_retries=5)


async def _send_webhook_async(webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send webhook asynchronously.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            return {
                "status": "success",
                "status_code": response.status_code,
                "response": response.text[:500]  # Truncate response
            }

        except Exception as e:
            logger.error(f"Webhook request failed: {e}")
            raise


@celery_app.task(base=TaskBase, name="process_pending_webhooks")
def process_pending_webhooks() -> Dict[str, Any]:
    """
    Periodic task to process pending webhooks.
    Checks database for tasks with webhooks that need to be sent.
    """
    # TODO: Implement database query for pending webhooks
    logger.info("Processing pending webhooks")

    return {
        "processed": 0,
        "failed": 0
    }


@celery_app.task(base=TaskBase, bind=True, name="send_email")
def send_email(
    self,
    to_email: str,
    subject: str,
    body: str,
    html: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send email notification.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        html: Optional HTML body

    Returns:
        Result with status
    """
    # TODO: Implement email sending with SMTP
    logger.info(f"Sending email to {to_email}: {subject}")

    return {
        "status": "not_implemented",
        "message": "Email sending not yet implemented"
    }