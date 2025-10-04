"""
DashScope API client for video animation services.
"""

import httpx
import logging
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class DashScopeClient:
    """Client for interacting with DashScope API."""

    def __init__(self):
        """Initialize DashScope client."""
        self.api_key = settings.QWEN_VIDEO_API_KEY
        self.base_url = settings.DASHSCOPE_API_URL
        self.timeout = settings.DASHSCOPE_TIMEOUT

    async def create_task(
        self,
        model: str,
        image_url: str,
        video_url: str,
        check_image: bool = True,
        mode: str = "wan-std"
    ) -> Dict[str, Any]:
        """
        Create a video animation task in DashScope.

        Args:
            model: Model name (wan2.2-animate-move or wan2.2-animate-mix)
            image_url: Input image URL
            video_url: Reference video URL
            check_image: Whether to check image quality
            mode: Processing mode (wan-std or wan-pro)

        Returns:
            Task creation response with task_id
        """
        headers = {
            "X-DashScope-Async": "enable",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "input": {
                "image_url": image_url,
                "video_url": video_url
            },
            "parameters": {
                "check_image": check_image,
                "mode": mode
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/services/aigc/image2video/video-synthesis/",
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                logger.error(f"DashScope API error: {response.text}")
                raise Exception(f"DashScope API error: {response.status_code}")

            result = response.json()
            return result.get("output", {})

    async def query_task(self, task_id: str) -> Dict[str, Any]:
        """
        Query task status from DashScope.

        Args:
            task_id: DashScope task ID

        Returns:
            Task status and results
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/tasks/{task_id}",
                headers=headers
            )

            if response.status_code != 200:
                logger.error(f"DashScope query error: {response.text}")
                raise Exception(f"DashScope query error: {response.status_code}")

            return response.json()

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: DashScope task ID

        Returns:
            True if successful
        """
        # DashScope doesn't support task cancellation yet
        logger.warning(f"Task cancellation not supported for task {task_id}")
        return False