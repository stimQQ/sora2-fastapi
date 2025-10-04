"""
Celery worker configuration and initialization.
"""

from celery import Celery
from celery.signals import worker_ready, worker_shutdown
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "video_animation_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "celery_app.tasks.video_tasks",
        "celery_app.tasks.notification_tasks",
        "celery_app.tasks.cleanup_tasks",
        "celery_app.tasks.credit_expiry_task",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=[settings.CELERY_TASK_SERIALIZER],
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    result_expires=settings.TASK_RESULT_EXPIRY,
    task_track_started=True,
    task_time_limit=settings.TASK_TIMEOUT,
    task_soft_time_limit=settings.TASK_TIMEOUT - 30,  # Soft limit 30 seconds before hard limit
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # Disable prefetching for long-running tasks
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks to prevent memory leaks
    beat_schedule={
        # Periodic tasks
        "cleanup-expired-tasks": {
            "task": "celery_app.tasks.cleanup_tasks.cleanup_expired_tasks",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-old-files": {
            "task": "celery_app.tasks.cleanup_tasks.cleanup_old_files",
            "schedule": 86400.0,  # Every day
        },
        "process-pending-webhooks": {
            "task": "celery_app.tasks.notification_tasks.process_pending_webhooks",
            "schedule": 60.0,  # Every minute
        },
        # Credit expiry tasks - Added 2025-09-30
        "expire-credits-daily": {
            "task": "celery_app.tasks.credit_expiry_task.expire_credits_daily",
            "schedule": 86400.0,  # Every day at midnight (controlled by timezone)
        },
        "check-expiring-credits-weekly": {
            "task": "celery_app.tasks.credit_expiry_task.check_expiring_credits",
            "schedule": 604800.0,  # Every week (7 days)
        },
    },
)

# Task routing
celery_app.conf.task_routes = {
    "celery_app.tasks.video_tasks.*": {"queue": "video_processing"},
    "celery_app.tasks.notification_tasks.*": {"queue": "notifications"},
    "celery_app.tasks.cleanup_tasks.*": {"queue": "cleanup"},
}

# Queue configuration
celery_app.conf.task_queues = {
    "default": {
        "exchange": "default",
        "exchange_type": "direct",
        "routing_key": "default",
    },
    "video_processing": {
        "exchange": "video",
        "exchange_type": "direct",
        "routing_key": "video.process",
    },
    "notifications": {
        "exchange": "notifications",
        "exchange_type": "direct",
        "routing_key": "notification.send",
    },
    "cleanup": {
        "exchange": "cleanup",
        "exchange_type": "direct",
        "routing_key": "cleanup.run",
    },
}


@worker_ready.connect
def on_worker_ready(**kwargs):
    """Called when worker is ready to accept tasks."""
    logger.info("Celery worker is ready")


@worker_shutdown.connect
def on_worker_shutdown(**kwargs):
    """Called when worker is shutting down."""
    logger.info("Celery worker is shutting down")


class TaskBase(celery_app.Task):
    """Base class for all tasks with common functionality."""

    autoretry_for = (Exception,)
    max_retries = settings.TASK_MAX_RETRIES
    default_retry_delay = settings.TASK_RETRY_DELAY

    def before_start(self, task_id: str, args: Any, kwargs: Any) -> None:
        """Called before task execution starts."""
        logger.info(f"Task {self.name} [{task_id}] starting")

    def on_success(self, retval: Any, task_id: str, args: Any, kwargs: Any) -> None:
        """Called when task succeeds."""
        logger.info(f"Task {self.name} [{task_id}] succeeded")

    def on_failure(self, exc: Exception, task_id: str, args: Any, kwargs: Any, einfo: Any) -> None:
        """Called when task fails."""
        logger.error(f"Task {self.name} [{task_id}] failed: {exc}", exc_info=einfo)

    def on_retry(self, exc: Exception, task_id: str, args: Any, kwargs: Any, einfo: Any) -> None:
        """Called when task is retried."""
        logger.warning(f"Task {self.name} [{task_id}] retrying: {exc}")