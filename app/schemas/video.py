"""
Pydantic schemas for video generation endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum


class AspectRatio(str, Enum):
    """Video aspect ratio options."""
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"


class Quality(str, Enum):
    """Video quality options."""
    STANDARD = "standard"
    HD = "hd"


# Text-to-Video Schemas
class TextToVideoRequest(BaseModel):
    """Request model for text-to-video generation."""
    prompt: str = Field(
        ...,
        description="Text description for video generation",
        min_length=1,
        max_length=5000
    )
    aspect_ratio: AspectRatio = Field(
        default=AspectRatio.LANDSCAPE,
        description="Video aspect ratio (landscape or portrait)"
    )
    quality: Quality = Field(
        default=Quality.STANDARD,
        description="Video quality (standard or hd)"
    )
    webhook_url: Optional[str] = Field(
        None,
        description="Webhook URL for task completion notification"
    )

    @validator("prompt")
    def validate_prompt(cls, v):
        """Validate prompt is not empty after stripping."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v.strip()


class TextToVideoResponse(BaseModel):
    """Response model for text-to-video task creation."""
    success: bool
    task_id: str
    message: str
    credits_estimated: int = Field(
        ...,
        description="Estimated credits that will be deducted upon completion"
    )
    estimated_time: Optional[int] = Field(
        None,
        description="Estimated processing time in seconds"
    )


# Image-to-Video Schemas
class ImageToVideoRequest(BaseModel):
    """Request model for image-to-video generation."""
    prompt: str = Field(
        ...,
        description="Text description of desired video action",
        min_length=1,
        max_length=5000
    )
    image_urls: List[str] = Field(
        ...,
        description="List of image URLs to animate",
        min_items=1
    )
    aspect_ratio: AspectRatio = Field(
        default=AspectRatio.LANDSCAPE,
        description="Video aspect ratio (landscape or portrait)"
    )
    quality: Quality = Field(
        default=Quality.STANDARD,
        description="Video quality (standard or hd)"
    )
    webhook_url: Optional[str] = Field(
        None,
        description="Webhook URL for task completion notification"
    )

    @validator("prompt")
    def validate_prompt(cls, v):
        """Validate prompt is not empty after stripping."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v.strip()

    @validator("image_urls")
    def validate_image_urls(cls, v):
        """Validate all image URLs are valid."""
        if not v:
            raise ValueError("At least one image URL is required")
        for url in v:
            if not url.strip():
                raise ValueError("Image URL cannot be empty")
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Invalid image URL: {url}")
        return v


class ImageToVideoResponse(BaseModel):
    """Response model for image-to-video task creation."""
    success: bool
    task_id: str
    message: str
    credits_estimated: int = Field(
        ...,
        description="Estimated credits that will be deducted upon completion"
    )
    estimated_time: Optional[int] = Field(
        None,
        description="Estimated processing time in seconds"
    )


# Sora Webhook Callback Schema
class SoraWebhookCallback(BaseModel):
    """Webhook callback from Sora API."""
    taskId: str = Field(..., description="Sora task ID")
    state: str = Field(..., description="Task state (waiting, success, fail)")
    resultJson: Optional[str] = Field(
        None,
        description="JSON string containing result URLs"
    )


# Sora Task Completion Schema (internal)
class SoraTaskCompletionRequest(BaseModel):
    """Internal request model for Sora task completion."""
    task_id: str = Field(..., description="Internal task ID")
    sora_task_id: str = Field(..., description="Sora API task ID")
    output_video_url: str = Field(..., description="URL of the completed video")
    task_type: str = Field(
        ...,
        description="Task type (text-to-video or image-to-video)"
    )
    quality: Quality = Field(..., description="Video quality used")


class SoraTaskCompletionResponse(BaseModel):
    """Response model for Sora task completion."""
    success: bool
    credits_deducted: int
    new_balance: int
    message: str
