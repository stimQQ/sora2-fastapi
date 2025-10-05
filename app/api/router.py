"""
Main API router - Simple structure without versioning.
"""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.tasks import router as tasks_router
from app.api.payments import router as payments_router
from app.api.videos import router as videos_router
from app.api.users import router as users_router
from app.api.showcase import router as showcase_router

# Create main API router
api_router = APIRouter(prefix="/api")

# Include all sub-routers
api_router.include_router(
    auth_router.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    tasks_router.router,
    prefix="/tasks",
    tags=["Tasks"]
)

api_router.include_router(
    payments_router.router,
    prefix="/payments",
    tags=["Payments"]
)

api_router.include_router(
    videos_router.router,
    prefix="/videos",
    tags=["Videos"]
)

api_router.include_router(
    users_router.router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    showcase_router.router,
    prefix="/showcase",
    tags=["Video Showcase"]
)