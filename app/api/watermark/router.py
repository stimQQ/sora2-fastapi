"""
Watermark Removal API Router

Endpoints:
- POST /watermark/remove - Submit watermark removal task
- GET /watermark/tasks/{task_id} - Query task status
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.db.base import get_db
from app.schemas.watermark import (
    WatermarkRemovalRequest,
    WatermarkRemovalResponse,
    WatermarkTaskStatusResponse
)
from app.services.watermark.wavespeed_service import WaveSpeedService
from app.core.dependencies import get_current_user_optional
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/remove", response_model=WatermarkRemovalResponse)
async def remove_watermark(
    request: WatermarkRemovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Submit a watermark removal task.

    **Authentication**: Requires either Bearer token or X-API-Key header

    **Request Body**:
    - `video_url`: URL of the video to process
    - `webhook_url` (optional): Callback URL for task completion notification

    **Response**:
    - `task_id`: Unique task identifier
    - `status`: Initial task status (usually "created")
    - `message`: Success message

    **Credits**: Will be deducted based on video duration
    """
    try:
        # Initialize WaveSpeed service
        wavespeed_service = WaveSpeedService(db)

        # Submit task
        result = await wavespeed_service.submit_removal_task(
            video_url=request.video_url,
            user=current_user,
            webhook_url=request.webhook_url
        )

        return WatermarkRemovalResponse(
            success=True,
            task_id=result["task_id"],
            status=result["status"],
            message="Watermark removal task submitted successfully",
            credits_estimated=result.get("credits_estimated", 0)
        )

    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit watermark removal task: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to submit watermark removal task"
        )


@router.get("/tasks/{task_id}", response_model=WatermarkTaskStatusResponse)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Query watermark removal task status.

    **Authentication**: Requires either Bearer token or X-API-Key header

    **Path Parameters**:
    - `task_id`: Task ID returned from the submission endpoint

    **Response**:
    - `task_id`: Task identifier
    - `status`: Current status (created, processing, completed, failed)
    - `progress`: Processing progress (0-100)
    - `result_url`: URL of processed video (available when completed)
    - `error_message`: Error details (if failed)
    - `created_at`: Task creation timestamp
    - `completed_at`: Task completion timestamp (if completed)

    **Status Values**:
    - `created`: Task queued
    - `processing`: Task being processed
    - `completed`: Task completed successfully
    - `failed`: Task failed
    """
    try:
        # Initialize WaveSpeed service
        wavespeed_service = WaveSpeedService(db)

        # Query task status
        result = await wavespeed_service.query_task_status(
            task_id=task_id,
            user=current_user
        )

        return WatermarkTaskStatusResponse(**result)

    except ValueError as e:
        logger.error(f"Task not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to query task status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to query task status"
        )
