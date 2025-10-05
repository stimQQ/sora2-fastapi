"""
Video processing API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, BackgroundTasks, status
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from datetime import datetime

from app.core.config import settings
from app.core.dependencies import get_current_user, verify_api_key, get_db
from app.services.dashscope.client import DashScopeClient
from app.services.sora.client import SoraClient, SoraAspectRatio, SoraQuality
from app.services.credits.manager import InsufficientCreditsError
from app.models.user import User
from app.schemas.video import (
    TextToVideoRequest,
    TextToVideoResponse,
    ImageToVideoRequest,
    ImageToVideoResponse,
    SoraWebhookCallback,
    SoraWebhookData
)

# Import Celery tasks only if not in serverless environment
import os
if os.getenv("VERCEL") != "1":
    from celery_app.tasks.video_tasks import process_video_animation, process_sora_video
else:
    # In Vercel, Celery tasks are not available
    process_video_animation = None
    process_sora_video = None

logger = logging.getLogger(__name__)

router = APIRouter()


class AnimateRequest(BaseModel):
    """Request model for animation tasks."""
    image_url: str = Field(..., description="URL of the input image")
    video_url: str = Field(..., description="URL of the reference video")
    check_image: bool = Field(default=True, description="Whether to check image quality")
    mode: str = Field(default="wan-std", description="Processing mode", pattern="^(wan-std|wan-pro|standard|pro)$")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for task completion")

    def get_normalized_mode(self) -> str:
        """Normalize mode to wan-std or wan-pro format."""
        mode_map = {
            "standard": "wan-std",
            "pro": "wan-pro",
            "wan-std": "wan-std",
            "wan-pro": "wan-pro"
        }
        return mode_map.get(self.mode, "wan-std")


class AnimateResponse(BaseModel):
    """Response model for animation tasks."""
    success: bool
    task_id: str
    message: str
    estimated_time: Optional[int] = Field(None, description="Estimated processing time in seconds")


class TaskStatusResponse(BaseModel):
    """Response model for task status query."""
    task_id: str
    status: str
    progress: Optional[float] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None


async def _validate_url(url: str, file_type: str) -> str:
    """
    Validate that URL is a public HTTP/HTTPS URL accessible by DashScope API.

    Args:
        url: Input URL (must be HTTP/HTTPS from OSS storage)
        file_type: 'image' or 'video' (for error messages)

    Returns:
        The validated URL

    Raises:
        HTTPException: If URL format is invalid
    """
    # Only accept HTTP/HTTPS URLs
    if url.startswith(('http://', 'https://')):
        return url

    # Reject base64 data URLs
    if url.startswith('data:'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Base64 data URLs are not supported for {file_type}. "
                   f"Please upload the file first using POST /api/videos/upload endpoint, "
                   f"then use the returned URL."
        )

    # Reject blob URLs
    if url.startswith('blob:'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Blob URLs are not supported for {file_type}. "
                   f"Please upload the file first using POST /api/videos/upload endpoint, "
                   f"then use the returned URL."
        )

    # Unknown URL format
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid {file_type} URL format. Must be a public HTTP/HTTPS URL from OSS storage. "
               f"Please upload the file first using POST /api/videos/upload endpoint."
    )


# Aliyun DashScope animate-move endpoint removed - not needed


# Aliyun DashScope animate-mix endpoint removed - not needed


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Query the status of a video generation task.
    Returns task information from database and optionally queries Sora API.
    """
    try:
        # Query task from database
        from app.models.task import Task
        result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Build response from database task
        response = TaskStatusResponse(
            task_id=task.id,
            status=task.status.value,
            created_at=task.created_at.isoformat() if task.created_at else "",
            updated_at=task.updated_at.isoformat() if task.updated_at else "",
            completed_at=task.completed_at.isoformat() if task.completed_at else None
        )

        # Add progress if available
        if task.progress is not None:
            response.progress = float(task.progress)

        # Add result URL if succeeded
        if task.status.value == "SUCCEEDED" and task.result_video_url:
            response.result_url = task.result_video_url

        # Add error message if failed
        elif task.status.value == "FAILED" and task.error_message:
            response.error_message = task.error_message

        # Optionally query Sora API for real-time status if task is pending/processing
        if task.sora_task_id and task.status.value in ["PENDING", "PROCESSING"]:
            try:
                client = SoraClient()
                sora_result = await client.query_task(task.sora_task_id)

                # Update response with Sora API data if available
                if sora_result and "status" in sora_result:
                    response.status = sora_result["status"]
                    if "progress" in sora_result:
                        response.progress = float(sora_result["progress"])

                    # If status changed, update database
                    if sora_result["status"] != task.status.value:
                        from app.models.task import TaskStatus
                        task.status = TaskStatus(sora_result["status"])
                        await db.commit()

            except Exception as sora_error:
                logger.warning(f"Failed to query Sora API for task {task_id}: {sora_error}")
                # Continue with database data

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TaskCompletionRequest(BaseModel):
    """Request model for task completion callback."""
    task_id: str = Field(..., description="Task ID")
    output_video_url: str = Field(..., description="URL of the completed video")
    duration_seconds: float = Field(..., description="Duration of output video in seconds", gt=0)
    is_pro: bool = Field(default=False, description="Whether pro version was used")


class TaskCompletionResponse(BaseModel):
    """Response model for task completion callback."""
    success: bool
    credits_deducted: int
    new_balance: int
    message: str


@router.post("/tasks/complete", response_model=TaskCompletionResponse)
async def complete_task(
    request: TaskCompletionRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Task completion callback endpoint.
    Called by Celery worker when a video task completes successfully.

    This is when credits are actually deducted based on the output video duration.

    Args:
        request: Task completion data
        db: Database session
        api_key: API key for internal service authentication

    Returns:
        Completion result with credits deducted

    Raises:
        HTTPException: If task not found, already processed, or insufficient credits
    """
    try:
        from app.services.credits.manager import CreditManager
        from app.models.task import Task

        logger.info(
            f"Task completion callback: task_id={request.task_id}, "
            f"duration={request.duration_seconds}s, is_pro={request.is_pro}"
        )

        # Get task from database
        task_stmt = select(Task).where(Task.id == request.task_id).with_for_update()
        task_result = await db.execute(task_stmt)
        task = task_result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found: {request.task_id}"
            )

        # Check if credits already deducted
        if task.credits_deducted:
            logger.warning(f"Credits already deducted for task {request.task_id}")
            return TaskCompletionResponse(
                success=True,
                credits_deducted=task.credits_calculated or 0,
                new_balance=0,  # We don't have access to current balance here
                message="Credits already deducted for this task"
            )

        # Calculate credits based on actual duration
        credits_required = CreditManager.calculate_video_credits(
            request.duration_seconds,
            request.is_pro
        )

        logger.info(
            f"Calculated credits for task {request.task_id}: {credits_required} credits "
            f"({request.duration_seconds}s × {'14' if request.is_pro else '10'} credits/s)"
        )

        # Deduct credits using FIFO expiry logic
        try:
            await CreditManager.deduct_with_expiry(
                user_id=task.user_id,
                amount=credits_required,
                reference_type="task_completion",
                reference_id=request.task_id,
                description=f"Video generation completed: {request.duration_seconds}s "
                           f"({'pro' if request.is_pro else 'standard'} mode)",
                db=db,
                task_id=request.task_id
            )

            # Update task record
            task.output_duration_seconds = request.duration_seconds
            task.credits_calculated = credits_required
            task.credits_deducted = True
            task.result_video_url = request.output_video_url

            # Get updated user balance
            user_stmt = select(User).where(User.id == task.user_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            new_balance = user.credits if user else 0

            await db.commit()

            logger.info(
                f"Successfully deducted {credits_required} credits for task {request.task_id}. "
                f"User new balance: {new_balance}"
            )

            return TaskCompletionResponse(
                success=True,
                credits_deducted=credits_required,
                new_balance=new_balance,
                message=f"Successfully deducted {credits_required} credits for {request.duration_seconds}s video"
            )

        except InsufficientCreditsError as e:
            # User doesn't have enough credits - this is a problem!
            # Log as error but don't rollback the task completion
            logger.error(
                f"Insufficient credits during task completion for task {request.task_id}: {e}. "
                f"Task will be marked as completed but credits not deducted."
            )

            # Mark task as completed but with credit issue
            task.output_duration_seconds = request.duration_seconds
            task.credits_calculated = credits_required
            task.credits_deducted = False
            task.result_video_url = request.output_video_url
            task.error_message = f"Insufficient credits during completion: {str(e)}"

            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(e)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete task {request.task_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task completion failed: {str(e)}"
        )


@router.post("/upload", tags=["File Upload"])
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = "image",
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    """
    Upload a file to storage and get its URL.
    Supports both images and videos.

    Args:
        file: File to upload
        file_type: Type of file (image or video)
        current_user: Authenticated user
        api_key: API key for service authentication

    Returns:
        Upload result with file URL and metadata

    Raises:
        HTTPException: If validation fails or upload fails
    """
    from app.services.storage.factory import get_storage_provider
    from io import BytesIO
    import uuid
    from datetime import datetime
    from urllib.parse import quote

    try:
        user_id = current_user.get("id")

        # Validate file type
        if file_type == "image":
            allowed_extensions = settings.ALLOWED_IMAGE_EXTENSIONS
        elif file_type == "video":
            allowed_extensions = settings.ALLOWED_VIDEO_EXTENSIONS
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Must be 'image' or 'video'"
            )

        # Validate filename exists
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )

        # Check file extension
        file_extension = f".{file.filename.split('.')[-1].lower()}"
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )

        # Read file contents
        contents = await file.read()

        # Check file size
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.1f}MB"
            )

        # Validate minimum file size (1KB)
        if len(contents) < 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too small. Minimum size: 1KB"
            )

        # Get storage provider
        storage_provider = get_storage_provider()

        # Generate unique storage key
        # Format: uploads/{file_type}/{user_id}/{YYYY/MM/DD}/{uuid}_{filename}
        date_path = datetime.utcnow().strftime("%Y/%m/%d")
        unique_id = str(uuid.uuid4())[:8]
        # Use ASCII-safe filename for storage key
        import re
        safe_filename = re.sub(r'[^\w\-_\.]', '_', file.filename)
        storage_key = f"uploads/{file_type}/{user_id}/{date_path}/{unique_id}_{safe_filename}"

        # Create BytesIO object for upload
        file_obj = BytesIO(contents)

        # Upload to storage
        logger.info(f"Uploading file: {storage_key}, Size: {len(contents)} bytes, User: {user_id}")

        # URL-encode the filename for metadata to handle Chinese characters
        file_url = await storage_provider.upload_file(
            file=file_obj,
            key=storage_key,
            content_type=file.content_type,
            metadata={
                "user_id": str(user_id),
                "original_filename": quote(file.filename),  # URL encode for latin-1 compatibility
                "file_type": file_type,
                "uploaded_at": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"File uploaded successfully: {storage_key}, URL: {file_url}")

        return {
            "success": True,
            "file_url": file_url,
            "storage_key": storage_key,
            "file_size": len(contents),
            "content_type": file.content_type,
            "file_type": file_type,
            "message": f"{file_type.capitalize()} uploaded successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@router.post("/text-to-video", response_model=TextToVideoResponse)
async def create_text_to_video_task(
    request: TextToVideoRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new text-to-video generation task using Sora 2.
    Generates video from text description.

    IMPORTANT: Credits are deducted immediately upon task creation.
    If the task fails, credits will be automatically refunded.

    Sora uses fixed pricing per video (not per second):
    - Standard quality: 20 credits
    - HD quality: 30 credits

    Requires authentication via JWT token in Authorization header.
    """
    try:
        user_id = current_user.get("id")

        # Calculate credits needed (fixed cost for Sora)
        from app.services.credits.manager import CreditManager
        credits_required = CreditManager.calculate_sora_credits(
            task_type="text-to-video",
            quality=request.quality.value
        )

        # Initialize Sora client
        client = SoraClient()

        # Create task with Sora API
        task_result = await client.create_text_to_video_task(
            prompt=request.prompt,
            aspect_ratio=SoraAspectRatio(request.aspect_ratio.value),
            quality=SoraQuality(request.quality.value),
            callback_url=request.webhook_url
        )

        sora_task_id = task_result.get("task_id")

        if not sora_task_id:
            raise HTTPException(status_code=500, detail="Failed to create Sora task")

        # Generate internal task ID
        import uuid
        task_id = str(uuid.uuid4())

        # Create task record FIRST (before credit deduction)
        from app.models.task import Task, TaskType, TaskStatus
        db_task = Task(
            id=task_id,
            user_id=user_id,
            task_type=TaskType.TEXT_TO_VIDEO,
            status=TaskStatus.PENDING,
            sora_task_id=sora_task_id,
            image_url=None,
            video_url=None,
            parameters={
                "prompt": request.prompt,
                "aspect_ratio": request.aspect_ratio.value,
                "quality": request.quality.value,
                "webhook_url": request.webhook_url,
                "credits_required": credits_required
            },
            credits_calculated=credits_required,
            started_at=datetime.utcnow()
        )
        db.add(db_task)
        await db.flush()  # Flush to insert task record

        # Now deduct credits (task record exists)
        try:
            await CreditManager.deduct_credits(
                user_id=user_id,
                amount=credits_required,
                reference_type="sora_task_creation",
                reference_id=task_id,
                description=f"Sora text-to-video ({request.quality.value}): {request.prompt[:50]}...",
                db=db,
                task_id=task_id
            )

            logger.info(
                f"Pre-deducted {credits_required} credits for Sora task {task_id}"
            )

        except Exception as deduct_error:
            logger.error(f"Failed to deduct credits for task {task_id}: {deduct_error}")
            await db.rollback()
            # If credit deduction fails, we should not proceed with the task
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Failed to deduct credits: {str(deduct_error)}"
            )

        # Commit both task and credit deduction
        await db.commit()

        # Queue async processing with Celery (only if not in Vercel serverless)
        if process_sora_video is not None:
            celery_task = process_sora_video.apply_async(
                args=(
                    task_id,
                    sora_task_id,
                    user_id,
                    "text-to-video",
                ),
                kwargs={
                    "parameters": {
                        "prompt": request.prompt,
                        "aspect_ratio": request.aspect_ratio.value,
                        "quality": request.quality.value,
                        "webhook_url": request.webhook_url,
                        "credits_required": credits_required
                    }
                },
                queue="video_processing"  # Explicitly specify queue
            )

            logger.info(
                f"Text-to-video task created: internal_id={task_id}, "
                f"sora_id={sora_task_id}, user={user_id}, quality={request.quality.value}, "
                f"credits={credits_required}, celery_task={celery_task.id}"
            )
        else:
            logger.info(
                f"Text-to-video task created in serverless mode: internal_id={task_id}, "
                f"sora_id={sora_task_id}, user={user_id}, quality={request.quality.value}, "
                f"credits={credits_required} (Celery not available in Vercel)"
            )

        return TextToVideoResponse(
            success=True,
            task_id=task_id,
            message="Text-to-video task created successfully. Credits deducted.",
            credits_estimated=credits_required,
            estimated_time=180  # 3 minutes estimated
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create text-to-video task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image-to-video", response_model=ImageToVideoResponse)
async def create_image_to_video_task(
    request: ImageToVideoRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new image-to-video generation task using Sora 2.
    Animates images based on text description.

    IMPORTANT: Credits are deducted immediately upon task creation.
    If the task fails, credits will be automatically refunded.

    Sora uses fixed pricing per video (not per second):
    - Standard quality: 25 credits
    - HD quality: 35 credits

    Requires authentication via JWT token in Authorization header.
    """
    try:
        user_id = current_user.get("id")

        # Calculate credits needed (fixed cost for Sora)
        from app.services.credits.manager import CreditManager
        credits_required = CreditManager.calculate_sora_credits(
            task_type="image-to-video",
            quality=request.quality.value
        )

        # Initialize Sora client
        client = SoraClient()

        # Create task with Sora API
        task_result = await client.create_image_to_video_task(
            prompt=request.prompt,
            image_urls=request.image_urls,
            aspect_ratio=SoraAspectRatio(request.aspect_ratio.value),
            quality=SoraQuality(request.quality.value),
            callback_url=request.webhook_url
        )

        sora_task_id = task_result.get("task_id")

        if not sora_task_id:
            raise HTTPException(status_code=500, detail="Failed to create Sora task")

        # Generate internal task ID
        import uuid
        task_id = str(uuid.uuid4())

        # Create task record FIRST (before credit deduction)
        from app.models.task import Task, TaskType, TaskStatus
        db_task = Task(
            id=task_id,
            user_id=user_id,
            task_type=TaskType.IMAGE_TO_VIDEO,
            status=TaskStatus.PENDING,
            sora_task_id=sora_task_id,
            image_url=request.image_urls[0] if request.image_urls else None,
            video_url=None,
            parameters={
                "prompt": request.prompt,
                "image_urls": request.image_urls,
                "aspect_ratio": request.aspect_ratio.value,
                "quality": request.quality.value,
                "webhook_url": request.webhook_url,
                "credits_required": credits_required
            },
            credits_calculated=credits_required,
            started_at=datetime.utcnow()
        )
        db.add(db_task)
        await db.flush()  # Flush to insert task record

        # Now deduct credits (task record exists)
        try:
            await CreditManager.deduct_credits(
                user_id=user_id,
                amount=credits_required,
                reference_type="sora_task_creation",
                reference_id=task_id,
                description=f"Sora image-to-video ({request.quality.value}): {request.prompt[:50]}...",
                db=db,
                task_id=task_id
            )

            logger.info(
                f"Pre-deducted {credits_required} credits for Sora task {task_id}"
            )

        except Exception as deduct_error:
            logger.error(f"Failed to deduct credits for task {task_id}: {deduct_error}")
            await db.rollback()
            # If credit deduction fails, we should not proceed with the task
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Failed to deduct credits: {str(deduct_error)}"
            )

        # Commit both task and credit deduction
        await db.commit()

        # Queue async processing with Celery (only if not in Vercel serverless)
        if process_sora_video is not None:
            celery_task = process_sora_video.apply_async(
                args=(
                    task_id,
                    sora_task_id,
                    user_id,
                    "image-to-video",
                ),
                kwargs={
                    "parameters": {
                        "prompt": request.prompt,
                        "image_urls": request.image_urls,
                        "aspect_ratio": request.aspect_ratio.value,
                        "quality": request.quality.value,
                        "webhook_url": request.webhook_url,
                        "credits_required": credits_required
                    }
                },
                queue="video_processing"  # Explicitly specify queue
            )

            logger.info(
                f"Image-to-video task created: internal_id={task_id}, "
                f"sora_id={sora_task_id}, user={user_id}, "
                f"images={len(request.image_urls)}, quality={request.quality.value}, "
                f"credits={credits_required}, celery_task={celery_task.id}"
            )
        else:
            logger.info(
                f"Image-to-video task created in serverless mode: internal_id={task_id}, "
                f"sora_id={sora_task_id}, user={user_id}, "
                f"images={len(request.image_urls)}, quality={request.quality.value}, "
                f"credits={credits_required} (Celery not available in Vercel)"
            )

        return ImageToVideoResponse(
            success=True,
            task_id=task_id,
            message="Image-to-video task created successfully. Credits deducted.",
            credits_estimated=credits_required,
            estimated_time=180  # 3 minutes estimated
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create image-to-video task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sora/callback", tags=["Sora Webhook"])
async def sora_webhook_callback(
    callback: SoraWebhookCallback,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook callback endpoint for Sora API task completion notifications.

    This endpoint is called by Sora API when a video generation task completes.
    It updates the task status and triggers credit deduction if successful.

    The callback content structure is identical to the Query Task API response.
    The `param` field contains the complete Create Task request parameters.

    Note: This endpoint does NOT require authentication as it's called by Sora API.
    However, in production, you should validate the callback signature/token.
    """
    try:
        from app.models.task import Task, TaskStatus
        from app.services.credits.manager import CreditManager
        import json

        # Handle error callback (code != 200)
        if callback.code != 200:
            logger.error(
                f"Received error callback from Sora: code={callback.code}, msg={callback.msg}"
            )

            # Try to find and update task even for error callbacks
            sora_task_id = callback.data.taskId if callback.data and callback.data.taskId else None

            if sora_task_id:
                task_stmt = select(Task).where(Task.sora_task_id == sora_task_id).with_for_update()
                task_result = await db.execute(task_stmt)
                task = task_result.scalar_one_or_none()

                if task:
                    # Update task to FAILED with error message
                    task.status = TaskStatus.FAILED
                    task.error_message = f"Sora API Error {callback.code}: {callback.msg}"
                    task.completed_at = datetime.utcnow()
                    task.progress = 0.0

                    # Refund credits if they were deducted
                    if task.credits_deducted:
                        parameters = task.parameters or {}
                        credits_to_refund = parameters.get("credits_required", 0)

                        if credits_to_refund > 0:
                            credit_manager = CreditManager()
                            await credit_manager.add_credits(
                                user_id=task.user_id,
                                amount=credits_to_refund,
                                reference_type="sora_task_refund",
                                reference_id=task.id,
                                description=f"Refund for failed Sora task: {callback.msg}",
                                db=db
                            )
                            logger.info(f"Refunded {credits_to_refund} credits for failed task {task.id}")

                    await db.commit()
                    logger.info(f"Updated task {task.id} to FAILED status with error: {callback.msg}")

            return {
                "success": True,
                "message": f"Error callback processed: {callback.msg}"
            }

        sora_task_id = callback.data.taskId
        state = callback.data.state

        logger.info(
            f"Received Sora webhook callback: task_id={sora_task_id}, "
            f"state={state}, model={callback.data.model}"
        )

        # Find task by sora_task_id
        task_stmt = select(Task).where(Task.sora_task_id == sora_task_id).with_for_update()
        task_result = await db.execute(task_stmt)
        task = task_result.scalar_one_or_none()

        if not task:
            logger.warning(f"Task not found for Sora task ID: {sora_task_id}")
            return {
                "success": False,
                "message": f"Task not found for Sora task ID: {sora_task_id}"
            }

        # Get credits amount for potential refund
        parameters = task.parameters or {}
        credits_required = parameters.get("credits_required", 0)

        # Handle based on state
        if state == "success":
            # Parse result JSON
            result_urls = []
            if callback.data.resultJson:
                try:
                    result_data = json.loads(callback.data.resultJson)
                    result_urls = result_data.get("resultUrls", [])
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse resultJson: {e}")

            if result_urls:
                video_url = result_urls[0]

                # Update task
                task.status = TaskStatus.SUCCEEDED
                task.result_video_url = video_url
                task.completed_at = datetime.utcnow()
                task.progress = 100.0
                # Mark credits as already deducted (happened at task creation)
                task.credits_deducted = True

                await db.commit()

                logger.info(
                    f"Sora task {task.id} marked as succeeded via webhook. "
                    f"Video URL: {video_url}. Credits already deducted at creation."
                )

                return {
                    "success": True,
                    "message": "Task completed successfully",
                    "task_id": task.id
                }
            else:
                # No result URLs - task failed, refund credits
                task.status = TaskStatus.FAILED
                task.error_message = "No video URL in webhook callback"
                task.completed_at = datetime.utcnow()

                # Refund credits since task failed
                if credits_required > 0:
                    try:
                        await CreditManager.refund_credits(
                            user_id=task.user_id,
                            amount=credits_required,
                            task_id=task.id,
                            reason="No video URL in webhook callback",
                            db=db
                        )

                        logger.info(
                            f"Refunded {credits_required} credits via webhook for failed task {task.id}"
                        )

                    except Exception as e:
                        logger.error(
                            f"Failed to refund credits via webhook for task {task.id}: {e}",
                            exc_info=True
                        )

                await db.commit()

                logger.error(f"No video URL in Sora webhook for task {task.id}")

                return {
                    "success": False,
                    "message": "No video URL in result",
                    "task_id": task.id
                }

        elif state == "fail":
            # Task failed - refund credits
            task.status = TaskStatus.FAILED
            task.error_message = "Sora task failed (webhook notification)"
            task.completed_at = datetime.utcnow()

            # Refund credits since task failed
            if credits_required > 0:
                try:
                    await CreditManager.refund_credits(
                        user_id=task.user_id,
                        amount=credits_required,
                        task_id=task.id,
                        reason="Sora task failed (webhook notification)",
                        db=db
                    )

                    logger.info(
                        f"Refunded {credits_required} credits via webhook for failed task {task.id}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to refund credits via webhook for task {task.id}: {e}",
                        exc_info=True
                    )

            await db.commit()

            logger.error(f"Sora task {task.id} failed (webhook notification)")

            return {
                "success": False,
                "message": "Task failed",
                "task_id": task.id
            }

        else:
            # Unknown state
            logger.warning(
                f"Unknown state '{state}' in Sora webhook for task {task.id}"
            )

            return {
                "success": False,
                "message": f"Unknown state: {state}",
                "task_id": task.id
            }

    except Exception as e:
        logger.error(f"Error processing Sora webhook callback: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )