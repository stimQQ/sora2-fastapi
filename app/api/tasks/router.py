"""
Task management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from app.core.dependencies import verify_api_key, get_current_user
from app.db.base import get_db_read, get_db_write

logger = logging.getLogger(__name__)

router = APIRouter()


class TaskResponse(BaseModel):
    """Task response model."""
    task_id: str
    user_id: str
    task_type: str
    status: str
    progress: Optional[float] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """Task list response."""
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    api_key: str = Depends(verify_api_key),
    db = Depends(get_db_read)
):
    """
    Get task details by ID.
    """
    from sqlalchemy import select
    from app.models.task import Task

    logger.info(f"Get task request: {task_id}")

    # Query task from database
    query = select(Task).where(Task.id == task_id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Map status to frontend format
    status_map = {
        "PENDING": "pending",
        "RUNNING": "processing",
        "SUCCEEDED": "completed",
        "FAILED": "failed",
        "CANCELLED": "failed",
        "TIMEOUT": "failed"
    }

    backend_status = task.status.value if hasattr(task.status, 'value') else task.status
    frontend_status = status_map.get(backend_status, "pending")

    return TaskResponse(
        task_id=task.id,
        user_id=str(task.user_id),
        task_type=task.task_type.value if hasattr(task.task_type, 'value') else task.task_type,
        status=frontend_status,
        progress=task.progress,
        result_url=task.result_video_url,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at
    )


@router.get("/user/tasks", response_model=TaskListResponse)
async def list_user_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_read)
):
    """
    List tasks for the current user.
    Supports pagination and filtering by status.
    """
    from sqlalchemy import select, func
    from app.models.task import Task

    logger.info(f"List tasks for user: {current_user.get('id')}")

    # Build query
    query = select(Task).where(Task.user_id == current_user.get('id'))

    # Filter by status if provided
    if status:
        query = query.where(Task.status == status)

    # Order by created_at descending (newest first)
    query = query.order_by(Task.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    tasks = result.scalars().all()

    # Map status to frontend format
    status_map = {
        "PENDING": "pending",
        "RUNNING": "processing",
        "SUCCEEDED": "completed",
        "FAILED": "failed",
        "CANCELLED": "failed",
        "TIMEOUT": "failed"
    }

    # Convert to response format
    task_responses = []
    for task in tasks:
        backend_status = task.status.value if hasattr(task.status, 'value') else task.status
        frontend_status = status_map.get(backend_status, "pending")

        task_responses.append(TaskResponse(
            task_id=task.id,
            user_id=str(task.user_id),
            task_type=task.task_type.value if hasattr(task.task_type, 'value') else task.task_type,
            status=frontend_status,
            progress=task.progress,
            result_url=task.result_video_url,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at
        ))

    return TaskListResponse(
        tasks=task_responses,
        total=total,
        page=page,
        page_size=page_size
    )


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_write)
):
    """
    Cancel a pending or running task.
    """
    from sqlalchemy import select, update
    from app.models.task import Task, TaskStatus

    logger.info(f"Cancel task request: {task_id} by user {current_user.get('id')}")

    # Query task
    query = select(Task).where(Task.id == task_id, Task.user_id == current_user.get('id'))
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if task can be cancelled
    if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status {task.status.value}"
        )

    # Update task status to CANCELLED
    update_query = (
        update(Task)
        .where(Task.id == task_id)
        .values(status=TaskStatus.CANCELLED, updated_at=datetime.utcnow())
    )
    await db.execute(update_query)
    await db.commit()

    # TODO: Cancel the actual processing job (Celery/DashScope/Sora)
    # For now, just update the status

    return {"message": "Task cancelled successfully"}


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_write)
):
    """
    Retry a failed task.
    Creates a new task with the same parameters.
    """
    from sqlalchemy import select
    from app.models.task import Task, TaskStatus, TaskType
    import uuid

    logger.info(f"Retry task request: {task_id} by user {current_user.get('id')}")

    # Query original task
    query = select(Task).where(Task.id == task_id, Task.user_id == current_user.get('id'))
    result = await db.execute(query)
    original_task = result.scalar_one_or_none()

    if not original_task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if task can be retried
    if not original_task.can_retry:
        raise HTTPException(
            status_code=400,
            detail="Task cannot be retried (either not failed or max retries reached)"
        )

    # Create a new task with the same parameters
    new_task_id = str(uuid.uuid4())
    new_task = Task(
        id=new_task_id,
        user_id=current_user.get('id'),
        task_type=original_task.task_type,
        status=TaskStatus.PENDING,
        image_url=original_task.image_url,
        video_url=original_task.video_url,
        parameters=original_task.parameters,
        retry_count=original_task.retry_count + 1,
        max_retries=original_task.max_retries,
    )

    db.add(new_task)
    await db.commit()

    # TODO: Submit the new task to the processing queue
    # For now, just create the task record

    return {
        "message": "Task retry initiated",
        "task_id": new_task_id,
        "original_task_id": task_id
    }