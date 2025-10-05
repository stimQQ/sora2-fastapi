"""
Video Showcase model for homepage video gallery.
Stores videos displayed on the homepage with their prompts.
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from sqlalchemy.sql import func
from datetime import datetime

from app.db.base import Base


class VideoShowcase(Base):
    """Video showcase model for homepage gallery."""

    __tablename__ = "video_showcases"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Video Information
    video_url = Column(String(500), nullable=False, comment="OSS video URL")
    prompt = Column(Text, nullable=False, comment="Video generation prompt")

    # Display Control
    is_active = Column(Boolean, default=True, nullable=False, index=True, comment="Whether to show on homepage")
    display_order = Column(Integer, default=0, nullable=False, index=True, comment="Display order (higher first)")

    # Metadata
    thumbnail_url = Column(String(500), nullable=True, comment="Video thumbnail URL (optional)")
    duration_seconds = Column(Integer, nullable=True, comment="Video duration in seconds")
    view_count = Column(Integer, default=0, nullable=False, comment="View count")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<VideoShowcase(id={self.id}, prompt={self.prompt[:30]}...)>"

    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "video_url": self.video_url,
            "prompt": self.prompt,
            "thumbnail_url": self.thumbnail_url,
            "duration_seconds": self.duration_seconds,
            "view_count": self.view_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
