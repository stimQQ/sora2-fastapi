"""
Video utility functions.
Handles video processing operations like duration extraction.
"""

import logging
import httpx
import subprocess
import tempfile
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


async def get_video_duration(video_url: str, timeout: int = 30) -> Optional[float]:
    """
    Get video duration from URL.

    This function downloads the video temporarily and uses ffprobe to extract duration.
    Falls back to metadata extraction if ffprobe is not available.

    Args:
        video_url: URL of the video file
        timeout: HTTP request timeout in seconds

    Returns:
        Duration in seconds (float), or None if unable to determine

    Raises:
        Exception: If video download or processing fails
    """
    try:
        logger.info(f"Extracting video duration from: {video_url}")

        # Download video to temporary file
        temp_file = None
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(video_url, follow_redirects=True)
                response.raise_for_status()

                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as f:
                    temp_file = f.name
                    f.write(response.content)
                    logger.info(f"Video downloaded to temp file: {temp_file}, size: {len(response.content)} bytes")

            # Try to get duration using ffprobe
            duration = await _get_duration_with_ffprobe(temp_file)

            if duration is not None:
                logger.info(f"Video duration extracted: {duration} seconds")
                return duration

            # Fallback: estimate from file size and bitrate (rough approximation)
            logger.warning("ffprobe not available or failed, using fallback estimation")
            file_size = os.path.getsize(temp_file)
            # Assume average bitrate of 1 Mbps for estimation
            estimated_duration = (file_size * 8) / (1024 * 1024)  # seconds
            logger.info(f"Estimated video duration: {estimated_duration} seconds (fallback)")
            return estimated_duration

        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file}: {e}")

    except httpx.HTTPError as e:
        logger.error(f"HTTP error downloading video {video_url}: {e}")
        raise Exception(f"Failed to download video: {str(e)}")
    except Exception as e:
        logger.error(f"Error extracting video duration from {video_url}: {e}")
        raise


async def _get_duration_with_ffprobe(file_path: str) -> Optional[float]:
    """
    Get video duration using ffprobe.

    Args:
        file_path: Path to video file

    Returns:
        Duration in seconds, or None if ffprobe fails
    """
    try:
        # Run ffprobe to get duration
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
            duration = float(result.stdout.strip())
            return duration
        else:
            logger.warning(f"ffprobe failed with code {result.returncode}: {result.stderr}")
            return None

    except FileNotFoundError:
        logger.warning("ffprobe not found in system PATH")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("ffprobe timeout")
        return None
    except Exception as e:
        logger.warning(f"ffprobe error: {e}")
        return None


def estimate_credits_for_task(duration_seconds: float, is_pro: bool = False) -> int:
    """
    Estimate credits required for a video task.

    Args:
        duration_seconds: Video duration in seconds
        is_pro: Whether pro version is used

    Returns:
        Estimated credits required
    """
    from app.core.config import settings

    rate = settings.CREDITS_PER_SECOND_PRO if is_pro else settings.CREDITS_PER_SECOND_STANDARD
    credits = int(duration_seconds * rate)

    # Always round up to ensure user has enough credits
    if duration_seconds * rate > credits:
        credits += 1

    return credits