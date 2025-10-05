"""
Pydantic schemas for video showcase endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class VideoShowcaseBase(BaseModel):
    """Base schema for VideoShowcase with required fields only."""
    video_url: str = Field(
        ...,
        description="OSS video URL",
        min_length=1,
        max_length=500
    )
    prompt: str = Field(
        ...,
        description="Video generation prompt",
        min_length=1
    )

    @validator("video_url")
    def validate_video_url(cls, v):
        """Validate video URL is not empty after stripping."""
        if not v.strip():
            raise ValueError("Video URL cannot be empty")
        return v.strip()

    @validator("prompt")
    def validate_prompt(cls, v):
        """Validate prompt is not empty after stripping."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v.strip()


class VideoShowcaseCreate(VideoShowcaseBase):
    """Schema for creating a new video showcase entry."""
    # Optional fields that can be provided at creation
    is_active: Optional[bool] = Field(
        default=True,
        description="Whether to show on homepage"
    )
    display_order: Optional[int] = Field(
        default=0,
        description="Display order (higher first)"
    )
    thumbnail_url: Optional[str] = Field(
        None,
        description="Video thumbnail URL (optional)",
        max_length=500
    )
    duration_seconds: Optional[int] = Field(
        None,
        description="Video duration in seconds",
        ge=0
    )
    view_count: Optional[int] = Field(
        default=0,
        description="View count",
        ge=0
    )


class VideoShowcaseUpdate(BaseModel):
    """Schema for updating a video showcase entry. All fields are optional."""
    video_url: Optional[str] = Field(
        None,
        description="OSS video URL",
        min_length=1,
        max_length=500
    )
    prompt: Optional[str] = Field(
        None,
        description="Video generation prompt",
        min_length=1
    )
    is_active: Optional[bool] = Field(
        None,
        description="Whether to show on homepage"
    )
    display_order: Optional[int] = Field(
        None,
        description="Display order (higher first)"
    )
    thumbnail_url: Optional[str] = Field(
        None,
        description="Video thumbnail URL (optional)",
        max_length=500
    )
    duration_seconds: Optional[int] = Field(
        None,
        description="Video duration in seconds",
        ge=0
    )
    view_count: Optional[int] = Field(
        None,
        description="View count",
        ge=0
    )


class VideoShowcaseResponse(VideoShowcaseBase):
    """Schema for video showcase response."""
    id: int = Field(..., description="Video showcase ID")

    # Optional fields in response
    is_active: Optional[bool] = Field(
        None,
        description="Whether to show on homepage"
    )
    display_order: Optional[int] = Field(
        None,
        description="Display order (higher first)"
    )
    thumbnail_url: Optional[str] = Field(
        None,
        description="Video thumbnail URL (optional)"
    )
    duration_seconds: Optional[int] = Field(
        None,
        description="Video duration in seconds"
    )
    view_count: Optional[int] = Field(
        None,
        description="View count"
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Last update timestamp"
    )

    class Config:
        from_attributes = True  # Pydantic v2 (orm_mode in v1)


class VideoShowcaseListResponse(BaseModel):
    """Schema for paginated video showcase list response."""
    total: int = Field(..., description="Total number of videos")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    videos: list[VideoShowcaseResponse] = Field(
        ...,
        description="List of video showcase items"
    )
