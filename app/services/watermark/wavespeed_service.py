"""
WaveSpeedAI API Service for watermark removal.

Handles interaction with WaveSpeedAI API endpoints.
"""

import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


class WaveSpeedService:
    """Service for interacting with WaveSpeedAI API."""

    BASE_URL = "https://api.wavespeed.ai/api/v3"
    TASK_ENDPOINT = "/wavespeed-ai/video-watermark-remover"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_key = settings.WAVESPEED_API_KEY
        if not self.api_key:
            logger.warning("WAVESPEED_API_KEY not configured")

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    async def submit_removal_task(
        self,
        video_url: str,
        user: Optional[User] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit watermark removal task to WaveSpeedAI.

        Args:
            video_url: URL of the video to process
            user: Current user (optional)
            webhook_url: Webhook URL for completion notification (optional)

        Returns:
            Dictionary containing task_id, status, and credits_estimated

        Raises:
            ValueError: If video_url is invalid
            Exception: If API request fails
        """
        if not video_url:
            raise ValueError("video_url is required")

        if not self.api_key:
            raise ValueError("WAVESPEED_API_KEY not configured")

        # Prepare request payload
        payload = {
            "video": str(video_url)
        }

        # TODO: Add webhook_url to payload if WaveSpeed API supports it
        # if webhook_url:
        #     payload["webhook_url"] = webhook_url

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}{self.TASK_ENDPOINT}",
                    headers=self._get_headers(),
                    json=payload
                )

                response.raise_for_status()
                result = response.json()

                # Extract task information from response
                if response.status_code == 200 and "data" in result:
                    task_data = result["data"]
                    task_id = task_data.get("id")
                    status = task_data.get("status", "created")

                    # TODO: Estimate credits based on video duration
                    # For now, use a fixed estimate
                    credits_estimated = 20

                    logger.info(f"Submitted watermark removal task: {task_id}")

                    return {
                        "task_id": task_id,
                        "status": status,
                        "credits_estimated": credits_estimated
                    }
                else:
                    raise Exception(f"Unexpected response: {result}")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from WaveSpeedAI: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to submit task: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error to WaveSpeedAI: {e}")
            raise Exception(f"Failed to connect to WaveSpeedAI: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error submitting task: {e}", exc_info=True)
            raise

    async def query_task_status(
        self,
        task_id: str,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Query task status from WaveSpeedAI.

        Args:
            task_id: Task ID returned from submit_removal_task
            user: Current user (optional)

        Returns:
            Dictionary containing task status and results

        Raises:
            ValueError: If task_id is invalid or task not found
            Exception: If API request fails
        """
        if not task_id:
            raise ValueError("task_id is required")

        if not self.api_key:
            raise ValueError("WAVESPEED_API_KEY not configured")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/predictions/{task_id}/result",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )

                response.raise_for_status()
                result = response.json()

                # Parse response
                if response.status_code == 200 and "data" in result:
                    task_data = result["data"]

                    status = task_data.get("status", "unknown")
                    outputs = task_data.get("outputs", [])
                    has_nsfw = task_data.get("has_nsfw_contents", [])
                    timings = task_data.get("timings", {})
                    error = task_data.get("error")
                    created_at = task_data.get("created_at")

                    # Calculate progress based on status
                    progress_map = {
                        "created": 0.0,
                        "processing": 50.0,
                        "completed": 100.0,
                        "failed": 0.0
                    }
                    progress = progress_map.get(status, 0.0)

                    return {
                        "task_id": task_id,
                        "status": status,
                        "progress": progress,
                        "result_url": outputs[0] if outputs else None,
                        "error_message": error,
                        "created_at": datetime.fromisoformat(created_at.replace('Z', '+00:00')) if created_at else datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        "completed_at": datetime.utcnow() if status == "completed" else None,
                        "has_nsfw_contents": has_nsfw[0] if has_nsfw else None,
                        "inference_time_ms": timings.get("inference")
                    }
                else:
                    raise ValueError(f"Task not found: {task_id}")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Task not found: {task_id}")
            logger.error(f"HTTP error from WaveSpeedAI: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to query task: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error to WaveSpeedAI: {e}")
            raise Exception(f"Failed to connect to WaveSpeedAI: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error querying task: {e}", exc_info=True)
            raise
