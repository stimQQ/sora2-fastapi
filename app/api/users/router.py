"""
User management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
import logging

from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class UserProfile(BaseModel):
    """User profile model."""
    id: str
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    region: str
    language: Optional[str] = None  # User preferred language (e.g., "zh-CN", "en")
    credits: int
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UpdateProfileRequest(BaseModel):
    """Update profile request."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    avatar_url: Optional[str] = None
    language: Optional[str] = Field(None, description="Preferred language (zh-CN, zh-TW, en, ja, ko)")


class CreditsResponse(BaseModel):
    """Credits balance response."""
    user_id: str
    credits: int
    total_earned: int
    total_spent: int


@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """
    Get current user profile.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.dependencies import get_db_read
    from app.models import User
    from sqlalchemy import select

    logger.info(f"Get profile for user: {current_user.get('id')}")

    # Get database session
    async for db in get_db_read():
        # Query user from database
        stmt = select(User).where(User.id == current_user.get("id"))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return UserProfile(
            id=str(user.id),  # Convert UUID to string
            email=user.email,
            username=user.username,
            avatar_url=user.avatar_url,
            region=user.region.value if user.region else "CN",
            language=user.language.value if user.language else None,
            credits=user.credits,
            created_at=user.created_at,
            last_login_at=user.last_login_at
        )


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user profile.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.dependencies import get_db_write
    from app.models import User
    from sqlalchemy import select

    logger.info(f"Update profile for user: {current_user.get('id')}")

    # Get database session
    async for db in get_db_write():
        # Query user from database
        stmt = select(User).where(User.id == current_user.get("id")).with_for_update()
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # Update user fields
        if request.username:
            user.username = request.username
        if request.avatar_url:
            user.avatar_url = request.avatar_url
        if request.language:
            # Validate language
            from app.models.user import UserLanguage
            try:
                user.language = UserLanguage(request.language)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid language. Allowed: {[lang.value for lang in UserLanguage]}"
                )

        await db.commit()
        await db.refresh(user)

        return UserProfile(
            id=str(user.id),  # Convert UUID to string
            email=user.email,
            username=user.username,
            avatar_url=user.avatar_url,
            region=user.region.value if user.region else "CN",
            language=user.language.value if user.language else None,
            credits=user.credits,
            created_at=user.created_at,
            last_login_at=user.last_login_at
        )


@router.get("/credits", response_model=CreditsResponse)
async def get_credits(current_user: dict = Depends(get_current_user)):
    """
    Get user credits balance.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.dependencies import get_db_read
    from fastapi import Depends as FastAPIDepends
    from app.models import User
    from sqlalchemy import select

    logger.info(f"Get credits for user: {current_user.get('id')}")

    # Get database session
    async for db in get_db_read():
        # Query user from database
        stmt = select(User).where(User.id == current_user.get("id"))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return CreditsResponse(
            user_id=str(user.id),
            credits=user.credits,
            total_earned=user.total_credits_earned,
            total_spent=user.total_credits_spent
        )


@router.delete("/account")
async def delete_account(current_user: dict = Depends(get_current_user)):
    """
    Delete user account.
    This is a soft delete that marks the account as inactive.
    """
    # TODO: Implement account deletion
    logger.info(f"Delete account request for user: {current_user.get('id')}")

    return {"message": "Account deletion requested. Your account will be deleted within 30 days."}