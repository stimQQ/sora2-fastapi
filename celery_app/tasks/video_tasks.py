"""
Celery tasks for video processing.
"""

import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import uuid

from celery_app.worker import celery_app, TaskBase
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(base=TaskBase, bind=True, name="process_video_animation")
def process_video_animation(
    self,
    task_id: str,
    user_id: str,
    task_type: str,
    image_url: str,
    video_url: str,
    parameters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Process video animation task asynchronously.

    Args:
        task_id: Database task ID
        user_id: User ID who created the task
        task_type: Type of animation (animate-move or animate-mix)
        image_url: Input image URL
        video_url: Input video URL
        parameters: Additional parameters

    Returns:
        Task result with status and output
    """
    try:
        logger.info(f"Processing video animation task {task_id} for user {user_id}")

        # Run async function in sync context
        result = asyncio.run(
            _process_video_animation_async(
                task_id, user_id, task_type, image_url, video_url, parameters
            )
        )

        return result

    except Exception as e:
        logger.error(f"Video animation task {task_id} failed: {e}")
        # Retry the task
        raise self.retry(exc=e)


async def _process_video_animation_async(
    task_id: str,
    user_id: str,
    task_type: str,
    image_url: str,
    video_url: str,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Async implementation of video animation processing.

    Note: The database task record is already created by the API endpoint,
    so this function updates the existing record rather than creating a new one.
    """
    from app.db.base import get_db_write
    from app.models.task import Task, TaskStatus
    from sqlalchemy import select

    parameters = parameters or {}

    # Get mode parameter
    mode = parameters.get("mode", "wan-std")
    is_pro = mode == "wan-pro"

    # Update task status to RUNNING
    async for db_session in get_db_write():
        try:
            # Get existing task record
            stmt = select(Task).where(Task.id == task_id).with_for_update()
            result = await db_session.execute(stmt)
            db_task = result.scalar_one_or_none()

            if not db_task:
                logger.error(f"Task {task_id} not found in database")
                raise Exception(f"Task {task_id} not found in database")

            # Get DashScope task ID from database
            dashscope_task_id = db_task.dashscope_task_id

            if not dashscope_task_id:
                logger.error(f"No DashScope task ID found for task {task_id}")
                raise Exception("No DashScope task ID found")

            # Update status to RUNNING
            db_task.status = TaskStatus.RUNNING
            await db_session.commit()

            logger.info(f"Updated task {task_id} status to RUNNING, DashScope ID: {dashscope_task_id}")
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            await db_session.rollback()
            raise
        finally:
            break

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Poll for task completion (DashScope task already created by API endpoint)
        task_result = await _poll_dashscope_task(dashscope_task_id, task_id)

        # If task succeeded, call completion endpoint to deduct credits
        if task_result.get("status") == "completed":
            output_video_url = task_result.get("video_url")

            if output_video_url:
                try:
                    # Get video duration
                    from app.utils.video import get_video_duration

                    duration = await get_video_duration(output_video_url)

                    logger.info(
                        f"Task {task_id} completed. Video duration: {duration}s. "
                        f"Calling completion endpoint to deduct credits..."
                    )

                    # Call completion endpoint to deduct credits
                    api_base_url = settings.API_BASE_URL if hasattr(settings, 'API_BASE_URL') else "http://localhost:8000"
                    completion_response = await client.post(
                        f"{api_base_url}/api/videos/tasks/complete",
                        headers={
                            "X-API-Key": settings.PROXY_API_KEY,
                            "Content-Type": "application/json"
                        },
                        json={
                            "task_id": task_id,
                            "output_video_url": output_video_url,
                            "duration_seconds": duration,
                            "is_pro": is_pro
                        }
                    )

                    if completion_response.status_code == 200:
                        completion_data = completion_response.json()
                        logger.info(
                            f"Credits deducted successfully for task {task_id}: "
                            f"{completion_data.get('credits_deducted')} credits. "
                            f"User new balance: {completion_data.get('new_balance')}"
                        )
                        task_result["credits_deducted"] = completion_data.get("credits_deducted")
                    else:
                        logger.error(
                            f"Failed to deduct credits for task {task_id}: "
                            f"HTTP {completion_response.status_code} - {completion_response.text}"
                        )
                        task_result["credit_deduction_error"] = completion_response.text

                except Exception as e:
                    logger.error(f"Error during credit deduction for task {task_id}: {e}", exc_info=True)
                    task_result["credit_deduction_error"] = str(e)
            else:
                logger.warning(f"No video URL in result for task {task_id}")

        elif task_result.get("status") == "failed":
            # Update task status to FAILED
            async for db_session in get_db_write():
                try:
                    stmt = select(Task).where(Task.id == task_id).with_for_update()
                    result = await db_session.execute(stmt)
                    db_task = result.scalar_one_or_none()

                    if db_task:
                        db_task.status = TaskStatus.FAILED
                        db_task.error_message = task_result.get("error_message", "Task failed")
                        db_task.completed_at = datetime.utcnow()
                        await db_session.commit()
                        logger.info(f"Updated task {task_id} status to FAILED")
                except Exception as e:
                    logger.error(f"Failed to update failed task status: {e}")
                    await db_session.rollback()
                finally:
                    break

        return task_result


async def _poll_dashscope_task(
    dashscope_task_id: str,
    task_id: str,
    max_attempts: int = 60,
    poll_interval: int = 10
) -> Dict[str, Any]:
    """
    Poll DashScope task status until completion.

    Args:
        dashscope_task_id: DashScope task ID
        task_id: Our database task ID
        max_attempts: Maximum number of polling attempts
        poll_interval: Seconds between polls

    Returns:
        Task result
    """
    headers = {
        "Authorization": f"Bearer {settings.QWEN_VIDEO_API_KEY}"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(max_attempts):
            # Query task status
            response = await client.get(
                f"{settings.DASHSCOPE_API_URL}/tasks/{dashscope_task_id}",
                headers=headers
            )

            if response.status_code != 200:
                logger.error(f"Failed to query DashScope task: {response.text}")
                continue

            data = response.json()
            output = data.get("output", {})
            task_status = output.get("task_status")

            logger.info(f"DashScope task {dashscope_task_id} status: {task_status}")

            if task_status == "SUCCEEDED":
                video_url = output.get("results", {}).get("video_url")

                return {
                    "status": "completed",
                    "dashscope_task_id": dashscope_task_id,
                    "video_url": video_url,
                    "usage": data.get("usage", {}),
                    "completed_at": datetime.utcnow().isoformat()
                }

            elif task_status == "FAILED":
                return {
                    "status": "failed",
                    "dashscope_task_id": dashscope_task_id,
                    "error_code": output.get("code"),
                    "error_message": output.get("message"),
                    "failed_at": datetime.utcnow().isoformat()
                }

            elif task_status in ["PENDING", "RUNNING"]:
                # Task still processing, wait and retry
                await asyncio.sleep(poll_interval)

            else:
                logger.warning(f"Unknown DashScope task status: {task_status}")

        # Timeout after max attempts
        return {
            "status": "timeout",
            "dashscope_task_id": dashscope_task_id,
            "error_message": f"Task timeout after {max_attempts * poll_interval} seconds",
            "timeout_at": datetime.utcnow().isoformat()
        }


@celery_app.task(base=TaskBase, name="check_video_task_status")
def check_video_task_status(dashscope_task_id: str) -> Dict[str, Any]:
    """
    Check the status of a DashScope video task.

    Args:
        dashscope_task_id: DashScope task ID

    Returns:
        Current task status
    """
    return asyncio.run(_check_dashscope_task_status(dashscope_task_id))


async def _check_dashscope_task_status(dashscope_task_id: str) -> Dict[str, Any]:
    """
    Check DashScope task status.
    """
    headers = {
        "Authorization": f"Bearer {settings.QWEN_VIDEO_API_KEY}"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{settings.DASHSCOPE_API_URL}/tasks/{dashscope_task_id}",
            headers=headers
        )

        if response.status_code != 200:
            raise Exception(f"Failed to query DashScope task: {response.text}")

        data = response.json()
        output = data.get("output", {})

        return {
            "task_id": dashscope_task_id,
            "status": output.get("task_status"),
            "results": output.get("results"),
            "usage": data.get("usage"),
            "submit_time": output.get("submit_time"),
            "scheduled_time": output.get("scheduled_time"),
            "end_time": output.get("end_time"),
        }


@celery_app.task(base=TaskBase, bind=True, name="process_sora_video")
def process_sora_video(
    self,
    task_id: str,
    sora_task_id: str,
    user_id: str,
    task_type: str,
    parameters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Process Sora video generation task asynchronously.

    Args:
        task_id: Internal database task ID
        sora_task_id: Sora API task ID
        user_id: User ID who created the task
        task_type: Type of task ('text-to-video' or 'image-to-video')
        parameters: Additional parameters including credits_required

    Returns:
        Task result with status and output
    """
    try:
        logger.info(
            f"Processing Sora video task: internal_id={task_id}, "
            f"sora_id={sora_task_id}, user={user_id}, type={task_type}"
        )

        # Run async function in sync context
        result = asyncio.run(
            _process_sora_video_async(
                task_id, sora_task_id, user_id, task_type, parameters
            )
        )

        return result

    except Exception as e:
        logger.error(f"Sora video task {task_id} failed: {e}", exc_info=True)
        # Retry the task
        raise self.retry(exc=e, max_retries=3, countdown=60)


async def _process_sora_video_async(
    task_id: str,
    sora_task_id: str,
    user_id: str,
    task_type: str,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Async implementation of Sora video processing.
    """
    from app.services.sora.client import SoraClient
    from app.db.base import get_db_write
    from app.models.task import Task, TaskType, TaskStatus
    from sqlalchemy import select

    parameters = parameters or {}
    quality = parameters.get("quality", "standard")
    credits_required = parameters.get("credits_required", 0)

    # Initialize Sora client
    client = SoraClient()

    # Update task status to RUNNING (task record already created by router)
    async for db_session in get_db_write():
        try:
            # Get existing task record
            stmt = select(Task).where(Task.id == task_id).with_for_update()
            result = await db_session.execute(stmt)
            db_task = result.scalar_one_or_none()

            if db_task:
                db_task.status = TaskStatus.RUNNING
                await db_session.commit()
                logger.info(f"Updated task {task_id} status to RUNNING")
            else:
                logger.warning(f"Task {task_id} not found in database, creating new record")
                # Fallback: create task record if not exists
                db_task = Task(
                    id=task_id,
                    user_id=user_id,
                    task_type=TaskType(task_type),
                    status=TaskStatus.RUNNING,
                    sora_task_id=sora_task_id,
                    image_url=parameters.get("image_urls", [None])[0] if task_type == "image-to-video" else None,
                    video_url=None,
                    parameters=parameters,
                    credits_calculated=credits_required,
                    started_at=datetime.utcnow()
                )
                db_session.add(db_task)
                await db_session.commit()
                logger.info(f"Created fallback database task record: {task_id}")
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            await db_session.rollback()
        finally:
            break

    # Poll for task completion
    task_result = await _poll_sora_task(client, sora_task_id, task_id)

    # Process based on result
    async for db_session in get_db_write():
        try:
            # Get task from database
            stmt = select(Task).where(Task.id == task_id).with_for_update()
            result = await db_session.execute(stmt)
            db_task = result.scalar_one_or_none()

            if not db_task:
                logger.error(f"Task {task_id} not found in database")
                break

            if task_result.get("state") == "success":
                # Task succeeded
                result_urls = task_result.get("result_urls", [])

                if result_urls:
                    video_url = result_urls[0]

                    # Update task as succeeded
                    db_task.status = TaskStatus.SUCCEEDED
                    db_task.result_video_url = video_url
                    db_task.completed_at = datetime.utcnow()
                    db_task.progress = 100.0
                    # Mark credits as already deducted (happened during task creation)
                    db_task.credits_deducted = True

                    await db_session.commit()

                    logger.info(
                        f"Sora task {task_id} completed successfully. "
                        f"Video URL: {video_url}. Credits already deducted at creation."
                    )

                    task_result["success"] = True
                else:
                    # No video URL in result - task failed, refund credits
                    db_task.status = TaskStatus.FAILED
                    db_task.error_message = "No video URL in Sora result"
                    db_task.completed_at = datetime.utcnow()

                    # Refund credits since task failed
                    from app.services.credits.manager import CreditManager

                    try:
                        await CreditManager.refund_credits(
                            user_id=user_id,
                            amount=credits_required,
                            task_id=task_id,
                            reason="No video URL in Sora result",
                            db=db_session
                        )

                        logger.info(
                            f"Refunded {credits_required} credits for failed task {task_id}"
                        )

                    except Exception as e:
                        logger.error(
                            f"Failed to refund credits for task {task_id}: {e}",
                            exc_info=True
                        )

                    await db_session.commit()

                    logger.error(f"No video URL in Sora result for task {task_id}")
                    task_result["success"] = False

            elif task_result.get("state") == "fail":
                # Task failed - refund credits
                db_task.status = TaskStatus.FAILED
                db_task.error_message = "Sora task failed"
                db_task.completed_at = datetime.utcnow()

                # Refund credits since task failed
                from app.services.credits.manager import CreditManager

                try:
                    await CreditManager.refund_credits(
                        user_id=user_id,
                        amount=credits_required,
                        task_id=task_id,
                        reason="Sora task failed",
                        db=db_session
                    )

                    logger.info(
                        f"Refunded {credits_required} credits for failed task {task_id}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to refund credits for task {task_id}: {e}",
                        exc_info=True
                    )

                await db_session.commit()

                logger.error(f"Sora task {task_id} failed")
                task_result["success"] = False

            else:
                # Timeout or unknown state - refund credits
                db_task.status = TaskStatus.TIMEOUT
                db_task.error_message = f"Task timeout or unknown state: {task_result.get('state')}"
                db_task.completed_at = datetime.utcnow()

                # Refund credits since task timed out
                from app.services.credits.manager import CreditManager

                try:
                    await CreditManager.refund_credits(
                        user_id=user_id,
                        amount=credits_required,
                        task_id=task_id,
                        reason=f"Task timeout or unknown state: {task_result.get('state')}",
                        db=db_session
                    )

                    logger.info(
                        f"Refunded {credits_required} credits for timed out task {task_id}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to refund credits for task {task_id}: {e}",
                        exc_info=True
                    )

                await db_session.commit()

                logger.warning(f"Sora task {task_id} timed out")
                task_result["success"] = False

        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}", exc_info=True)
            await db_session.rollback()
        finally:
            break

    return task_result


async def _poll_sora_task(
    client,
    sora_task_id: str,
    task_id: str,
    max_attempts: int = 60,
    poll_interval: int = 10
) -> Dict[str, Any]:
    """
    Poll Sora task status until completion.

    Args:
        client: SoraClient instance
        sora_task_id: Sora API task ID
        task_id: Our internal task ID
        max_attempts: Maximum number of polling attempts (default: 60 = 10 minutes)
        poll_interval: Seconds between polls (default: 10s)

    Returns:
        Task result with state and result_urls
    """
    for attempt in range(max_attempts):
        try:
            # Query task status
            result = await client.query_task(sora_task_id)
            state = result.get("state")

            logger.info(
                f"Sora task {sora_task_id} status: {state} "
                f"(attempt {attempt + 1}/{max_attempts})"
            )

            if state == "success":
                # Task completed successfully
                return result

            elif state == "fail":
                # Task failed
                logger.error(f"Sora task {sora_task_id} failed")
                return result

            elif state == "waiting":
                # Task still processing, wait and retry
                await asyncio.sleep(poll_interval)

            else:
                # Unknown state
                logger.warning(f"Unknown Sora task state: {state}")
                await asyncio.sleep(poll_interval)

        except Exception as e:
            logger.error(
                f"Error polling Sora task {sora_task_id}: {e}",
                exc_info=True
            )
            await asyncio.sleep(poll_interval)

    # Timeout after max attempts
    logger.error(
        f"Sora task {sora_task_id} timed out after "
        f"{max_attempts * poll_interval} seconds"
    )

    return {
        "state": "timeout",
        "task_id": sora_task_id,
        "result_urls": [],
        "error": f"Task timeout after {max_attempts * poll_interval} seconds"
    }