"""
Pydantic schemas for watermark removal API.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime


class WatermarkRemovalRequest(BaseModel):
    """Request schema for submitting watermark removal task."""

    video_url: HttpUrl = Field(
        ...,
        description="URL of the video to remove watermark from"
    )
    webhook_url: Optional[HttpUrl] = Field(
        None,
        description="Callback URL for task completion notification"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "video_url": "https://oss.example.com/videos/input.mp4",
                "webhook_url": "https://your-domain.com/webhook"
            }
        }
    }


class WatermarkRemovalResponse(BaseModel):
    """Response schema for watermark removal task submission."""

    success: bool = Field(..., description="Whether the task was submitted successfully")
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Initial task status")
    message: str = Field(..., description="Success message")
    credits_estimated: int = Field(
        0,
        description="Estimated credits to be consumed"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "task_id": "abc123-def456-ghi789",
                "status": "created",
                "message": "Watermark removal task submitted successfully",
                "credits_estimated": 20
            }
        }
    }


class WatermarkTaskStatusResponse(BaseModel):
    """Response schema for querying task status."""

    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Current task status")
    progress: float = Field(
        0.0,
        ge=0.0,
        le=100.0,
        description="Processing progress (0-100)"
    )
    result_url: Optional[str] = Field(
        None,
        description="URL of the processed video (available when completed)"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error details (if failed)"
    )
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: Optional[datetime] = Field(
        None,
        description="Last update timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Task completion timestamp"
    )
    has_nsfw_contents: Optional[bool] = Field(
        None,
        description="Whether NSFW content was detected"
    )
    inference_time_ms: Optional[int] = Field(
        None,
        description="Inference time in milliseconds"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "abc123-def456-ghi789",
                "status": "completed",
                "progress": 100.0,
                "result_url": "https://oss.example.com/videos/output.mp4",
                "error_message": None,
                "created_at": "2025-10-06T00:00:00Z",
                "updated_at": "2025-10-06T00:02:00Z",
                "completed_at": "2025-10-06T00:02:00Z",
                "has_nsfw_contents": False,
                "inference_time_ms": 120000
            }
        }
    }
