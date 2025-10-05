"""
Task model for video processing tasks.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class TaskType(str, enum.Enum):
    """Task type enumeration."""
    ANIMATE_MOVE = "ANIMATE_MOVE"
    ANIMATE_MIX = "ANIMATE_MIX"
    TEXT_TO_VIDEO = "TEXT_TO_VIDEO"
    IMAGE_TO_VIDEO = "IMAGE_TO_VIDEO"


class TaskStatus(str, enum.Enum):
    """Task status enumeration."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class Task(Base):
    """Video processing task model."""

    __tablename__ = "tasks"

    # Primary Key
    id = Column(String(36), primary_key=True, index=True)

    # User Reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Task Information
    task_type = Column(SQLEnum(TaskType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    status = Column(SQLEnum(TaskStatus, values_callable=lambda obj: [e.value for e in obj]), default=TaskStatus.PENDING, nullable=False, index=True)

    # DashScope Integration
    dashscope_task_id = Column(String(100), unique=True, index=True, nullable=True)

    # Sora Integration (for text-to-video and image-to-video)
    sora_task_id = Column(String(100), unique=True, index=True, nullable=True)

    # Input Files (nullable for text-to-video tasks)
    # Using Text to support base64 encoded data URLs and long URLs
    image_url = Column(Text, nullable=True)
    video_url = Column(Text, nullable=True)

    # Output (increased to 2000 for Sora signed URLs with long query parameters)
    result_video_url = Column(String(2000), nullable=True)

    # Parameters
    parameters = Column(JSON, nullable=True)

    # Progress
    progress = Column(Float, default=0.0, nullable=False)

    # Error Information
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # Webhook
    webhook_url = Column(String(500), nullable=True)
    webhook_sent = Column(Integer, default=0, nullable=False)  # Number of webhook attempts

    # Credits - Updated 2025-09-30
    credits_cost = Column(Integer, default=0, nullable=False)  # Deprecated: Kept for backward compatibility
    output_duration_seconds = Column(Float, nullable=True)  # Actual output video duration
    credits_calculated = Column(Integer, nullable=True)  # Calculated credits based on duration
    credits_deducted = Column(Boolean, default=False, nullable=False)  # Whether credits have been deducted

    # Retry
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Celery Task ID
    celery_task_id = Column(String(100), nullable=True, index=True)

    def __repr__(self):
        return f"<Task(id={self.id}, type={self.task_type}, status={self.status})>"

    @property
    def is_final_status(self) -> bool:
        """Check if task is in a final status."""
        return self.status in [
            TaskStatus.SUCCEEDED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMEOUT
        ]

    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries