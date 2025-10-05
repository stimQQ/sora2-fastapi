"""
Video Showcase API endpoints.
Provides video gallery for homepage display.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import List, Optional
import logging

from app.db.base import get_db
from app.models.video_showcase import VideoShowcase
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/videos", response_model=dict)
async def get_showcase_videos(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of showcase videos for homepage.

    Only returns active videos, ordered by display_order (desc) and created_at (desc).
    Video URLs are automatically converted to CDN URLs if configured.
    """
    try:
        # Count total active videos
        count_query = select(func.count(VideoShowcase.id)).where(
            VideoShowcase.is_active == True
        )
        result = await db.execute(count_query)
        total = result.scalar()

        # Get paginated videos
        offset = (page - 1) * page_size
        query = (
            select(VideoShowcase)
            .where(VideoShowcase.is_active == True)
            .order_by(VideoShowcase.display_order.desc(), VideoShowcase.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await db.execute(query)
        videos = result.scalars().all()

        # Convert to dict and add CDN URLs
        video_list = []
        for video in videos:
            video_data = video.to_dict()
            # Add CDN URL if configured
            video_data["video_url"] = _get_cdn_url(video.video_url)
            if video.thumbnail_url:
                video_data["thumbnail_url"] = _get_cdn_url(video.thumbnail_url)
            video_list.append(video_data)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "videos": video_list
        }

    except Exception as e:
        logger.error(f"Error fetching showcase videos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch videos")


@router.get("/videos/{video_id}", response_model=dict)
async def get_video_detail(
    video_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get single video detail and increment view count."""
    try:
        # Get video
        query = select(VideoShowcase).where(
            VideoShowcase.id == video_id,
            VideoShowcase.is_active == True
        )
        result = await db.execute(query)
        video = result.scalar_one_or_none()

        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Increment view count
        await db.execute(
            update(VideoShowcase)
            .where(VideoShowcase.id == video_id)
            .values(view_count=VideoShowcase.view_count + 1)
        )
        await db.commit()

        # Convert to dict and add CDN URLs
        video_data = video.to_dict()
        video_data["video_url"] = _get_cdn_url(video.video_url)
        if video.thumbnail_url:
            video_data["thumbnail_url"] = _get_cdn_url(video.thumbnail_url)

        return video_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching video {video_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch video")


def _get_cdn_url(oss_url: str) -> str:
    """
    Convert OSS URL to CDN URL if CDN is configured.

    Example:
        OSS: https://bucket.oss-cn-beijing.aliyuncs.com/path/to/video.mp4
        CDN: https://cdn.yourdomain.com/path/to/video.mp4
    """
    if not oss_url:
        return oss_url

    # Check if CDN domain is configured
    cdn_domain = getattr(settings, 'ALIYUN_OSS_CDN_DOMAIN', None)

    if not cdn_domain:
        return oss_url

    # Replace OSS domain with CDN domain
    oss_endpoint = settings.ALIYUN_OSS_ENDPOINT.replace('https://', '').replace('http://', '')
    bucket_name = settings.ALIYUN_OSS_BUCKET
    oss_domain = f"{bucket_name}.{oss_endpoint}"

    if oss_domain in oss_url:
        return oss_url.replace(oss_domain, cdn_domain)

    return oss_url
