"""
Celery tasks package.
"""

# Import all task modules here for auto-discovery
from celery_app.tasks import video_tasks
from celery_app.tasks import notification_tasks
from celery_app.tasks import cleanup_tasks

__all__ = [
    "video_tasks",
    "notification_tasks",
    "cleanup_tasks",
]