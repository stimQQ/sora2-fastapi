"""
Sora 2 API client for video generation services.
Supports both text-to-video and image-to-video generation.
"""

import httpx
import logging
import json
from typing import Dict, Any, Optional, List
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)


class SoraModel(str, Enum):
    """Sora 2 model types."""
    TEXT_TO_VIDEO = "sora-2-text-to-video"
    IMAGE_TO_VIDEO = "sora-2-image-to-video"


class SoraAspectRatio(str, Enum):
    """Supported aspect ratios."""
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"


class SoraQuality(str, Enum):
    """Video quality options."""
    STANDARD = "standard"
    HD = "hd"


class SoraTaskState(str, Enum):
    """Sora task states."""
    WAITING = "waiting"
    SUCCESS = "success"
    FAIL = "fail"


class SoraClient:
    """Client for interacting with Sora 2 API (kie.ai)."""

    def __init__(self):
        """Initialize Sora client with API configuration."""
        self.api_key = settings.SORA_API_KEY
        self.base_url = settings.SORA_API_URL
        self.timeout = settings.SORA_TIMEOUT
        self.callback_url = getattr(settings, 'SORA_CALLBACK_URL', None)

    async def create_text_to_video_task(
        self,
        prompt: str,
        aspect_ratio: SoraAspectRatio = SoraAspectRatio.LANDSCAPE,
        quality: SoraQuality = SoraQuality.STANDARD,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a text-to-video generation task.

        Args:
            prompt: Text description for video generation (max 5000 characters)
            aspect_ratio: Video aspect ratio (landscape or portrait)
            quality: Video quality (standard or hd)
            callback_url: Optional webhook URL for task completion notification

        Returns:
            Task creation response with task_id

        Raises:
            Exception: If API request fails
        """
        if len(prompt) > 5000:
            raise ValueError("Prompt must be 5000 characters or less")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": SoraModel.TEXT_TO_VIDEO.value,
            "input": {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio.value,
                "quality": quality.value
            }
        }

        # Add callback URL if provided
        if callback_url or self.callback_url:
            payload["callBackUrl"] = callback_url or self.callback_url

        logger.info(
            f"Creating Sora text-to-video task: prompt_length={len(prompt)}, "
            f"aspect_ratio={aspect_ratio.value}, quality={quality.value}"
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/jobs/createTask",
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                logger.error(
                    f"Sora API error: status={response.status_code}, "
                    f"body={response.text}"
                )
                raise Exception(
                    f"Sora API error: {response.status_code} - {response.text}"
                )

            result = response.json()

            # Validate response structure
            if result.get("code") != 200:
                error_msg = result.get("msg", "Unknown error")
                logger.error(f"Sora API returned error: {error_msg}")
                raise Exception(f"Sora API error: {error_msg}")

            data = result.get("data", {})
            task_id = data.get("taskId")

            if not task_id:
                raise Exception("Sora API did not return taskId in response")

            logger.info(
                f"Sora text-to-video task created successfully: "
                f"task_id={task_id}, aspect_ratio={aspect_ratio.value}, "
                f"quality={quality.value}"
            )

            return {
                "task_id": task_id,
                "state": data.get("state", "waiting"),
                "raw_response": result
            }

    async def create_image_to_video_task(
        self,
        prompt: str,
        image_urls: List[str],
        aspect_ratio: SoraAspectRatio = SoraAspectRatio.LANDSCAPE,
        quality: SoraQuality = SoraQuality.STANDARD,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an image-to-video generation task.

        Args:
            prompt: Text description of desired video action
            image_urls: List of image URLs to animate
            aspect_ratio: Video aspect ratio (landscape or portrait)
            quality: Video quality (standard or hd)
            callback_url: Optional webhook URL for task completion notification

        Returns:
            Task creation response with task_id

        Raises:
            ValueError: If input validation fails
            Exception: If API request fails
        """
        if len(prompt) > 5000:
            raise ValueError("Prompt must be 5000 characters or less")

        if not image_urls or len(image_urls) == 0:
            raise ValueError("At least one image URL is required")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": SoraModel.IMAGE_TO_VIDEO.value,
            "input": {
                "prompt": prompt,
                "image_urls": image_urls,
                "aspect_ratio": aspect_ratio.value,
                "quality": quality.value
            }
        }

        # Add callback URL if provided
        if callback_url or self.callback_url:
            payload["callBackUrl"] = callback_url or self.callback_url

        logger.info(
            f"Creating Sora image-to-video task: prompt_length={len(prompt)}, "
            f"images={len(image_urls)}, aspect_ratio={aspect_ratio.value}, "
            f"quality={quality.value}"
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/jobs/createTask",
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                logger.error(
                    f"Sora API error: status={response.status_code}, "
                    f"body={response.text}"
                )
                raise Exception(
                    f"Sora API error: {response.status_code} - {response.text}"
                )

            result = response.json()

            # Validate response structure
            if result.get("code") != 200:
                error_msg = result.get("msg", "Unknown error")
                logger.error(f"Sora API returned error: {error_msg}")
                raise Exception(f"Sora API error: {error_msg}")

            data = result.get("data", {})
            task_id = data.get("taskId")

            if not task_id:
                raise Exception("Sora API did not return taskId in response")

            logger.info(
                f"Sora image-to-video task created successfully: "
                f"task_id={task_id}, images={len(image_urls)}, "
                f"aspect_ratio={aspect_ratio.value}, quality={quality.value}"
            )

            return {
                "task_id": task_id,
                "state": data.get("state", "waiting"),
                "raw_response": result
            }

    async def query_task(self, task_id: str) -> Dict[str, Any]:
        """
        Query the status of a Sora task.

        Args:
            task_id: Sora task ID

        Returns:
            Task status and results

        Response format (matches API documentation exactly):
            {
                "code": 200,
                "msg": "success",
                "data": {
                    "taskId": "xxx",
                    "model": "sora-2-text-to-video",
                    "state": "waiting|success|fail",
                    "param": "{...}",  # JSON string of complete request params
                    "resultJson": "{\"resultUrls\":[\"video_url\"]}",  # JSON string
                    "failCode": null,
                    "failMsg": null,
                    "costTime": null,
                    "completeTime": null,
                    "createTime": 1757584164490
                }
            }

        Raises:
            Exception: If API request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/jobs/recordInfo",
                headers=headers,
                params={"taskId": task_id}
            )

            if response.status_code != 200:
                logger.error(
                    f"Sora query error: status={response.status_code}, "
                    f"body={response.text}"
                )
                raise Exception(
                    f"Sora query error: {response.status_code} - {response.text}"
                )

            result = response.json()

            # Validate response
            if result.get("code") != 200:
                error_msg = result.get("msg", "Unknown error")
                logger.error(f"Sora API query error: {error_msg}")
                raise Exception(f"Sora API error: {error_msg}")

            data = result.get("data", {})
            state = data.get("state", "waiting")

            logger.debug(f"Sora task {task_id} status: {state}")

            # Parse result JSON if task succeeded
            result_urls = []
            if state == SoraTaskState.SUCCESS.value:
                result_json_str = data.get("resultJson", "{}")
                try:
                    result_json = json.loads(result_json_str)
                    result_urls = result_json.get("resultUrls", [])
                    logger.info(
                        f"Sora task {task_id} succeeded with {len(result_urls)} "
                        f"result URL(s)"
                    )
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Failed to parse resultJson for task {task_id}: {e}"
                    )

            return {
                "task_id": task_id,
                "state": state,
                "result_urls": result_urls,
                "raw_data": data
            }

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running Sora task.

        Note: Sora API may not support task cancellation.
        This is a placeholder for future implementation.

        Args:
            task_id: Sora task ID

        Returns:
            True if successful, False otherwise
        """
        logger.warning(
            f"Task cancellation not yet implemented for Sora task {task_id}"
        )
        return False
