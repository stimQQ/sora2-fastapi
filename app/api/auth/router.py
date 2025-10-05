"""
Authentication API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
import logging
import re
import secrets

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.core.dependencies import get_current_user
from app.models.user import User, AuthProvider
from app.db.base import get_redis

logger = logging.getLogger(__name__)

router = APIRouter()




class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class SendSMSRequest(BaseModel):
    """Send SMS verification code request."""
    phone_number: str = Field(..., description="Phone number with country code (e.g., 86-13800138000)")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        # Remove spaces and dashes for validation
        phone = v.replace(' ', '').replace('-', '')

        # Check if it's all digits after removing country code separator
        if not re.match(r'^\d+$', phone):
            raise ValueError('Phone number must contain only digits and optional country code separator')

        # Check length (between 10-15 digits is reasonable)
        if len(phone) < 10 or len(phone) > 15:
            raise ValueError('Phone number must be between 10-15 digits')

        return v


class VerifySMSRequest(BaseModel):
    """Verify SMS code and login request."""
    phone_number: str = Field(..., description="Phone number with country code")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username for new user registration")

    @validator('code')
    def validate_code(cls, v):
        """Validate verification code is numeric."""
        if not v.isdigit():
            raise ValueError('Verification code must be numeric')
        return v

    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        phone = v.replace(' ', '').replace('-', '')
        if not re.match(r'^\d+$', phone):
            raise ValueError('Phone number must contain only digits')
        if len(phone) < 10 or len(phone) > 15:
            raise ValueError('Phone number must be between 10-15 digits')
        return v


class UserResponse(BaseModel):
    """User response model."""
    id: str
    phone_number: Optional[str] = None
    username: str
    credits: int
    is_new_user: bool = False


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    """
    # TODO: Implement refresh token validation and rotation
    logger.info("Token refresh request")

    # Mock response
    user_id = "user_12345"

    access_token = create_access_token(
        data={"sub": user_id}
    )
    refresh_token = create_refresh_token(
        data={"sub": user_id}
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout user.
    Invalidates the current token.
    """
    # TODO: Implement token blacklisting with Redis
    logger.info(f"User {current_user.get('id')} logged out")

    return {"message": "Successfully logged out"}


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return current_user


# WeChat OAuth endpoints
@router.post("/wechat/login")
async def wechat_login(code: str):
    """
    WeChat OAuth login.
    Exchange authorization code for access token.
    """
    # TODO: Implement WeChat OAuth flow
    logger.info(f"WeChat login with code: {code}")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="WeChat OAuth not yet implemented"
    )


# Google OAuth endpoints
class GoogleLoginRequest(BaseModel):
    """Google OAuth login request."""
    code: str = Field(..., description="Authorization code from Google OAuth")
    redirect_uri: Optional[str] = Field(None, description="Redirect URI used in OAuth flow")


@router.post("/google/login", response_model=TokenResponse)
async def google_login(request: GoogleLoginRequest):
    """
    Google OAuth login.
    Exchange authorization code for access token and create/login user.

    Args:
        request: Google login request with authorization code

    Returns:
        JWT access token and refresh token

    Raises:
        HTTPException: If authentication fails
    """
    from app.services.auth.providers.google_oauth import google_oauth_provider
    from app.db.base import get_db_write
    from sqlalchemy import select
    import uuid

    try:
        logger.info("Processing Google OAuth login")

        # Authenticate with Google
        user_info = await google_oauth_provider.authenticate(
            request.code,
            request.redirect_uri
        )

        # Get database session
        async for db in get_db_write():
            # Check if user exists by Google ID
            stmt = select(User).where(User.google_id == user_info["google_id"])
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                # Check if user exists by email
                if user_info.get("email"):
                    stmt = select(User).where(User.email == user_info["email"])
                    result = await db.execute(stmt)
                    user = result.scalar_one_or_none()

                    if user:
                        # Link Google account to existing user
                        user.google_id = user_info["google_id"]
                        user.avatar_url = user_info.get("picture") or user.avatar_url
                        logger.info(f"Linked Google account to existing user: {user.id}")
                    else:
                        # Create new user
                        user = await _create_google_user(db, user_info)
                else:
                    # Create new user without email
                    user = await _create_google_user(db, user_info)

            # Update user profile from Google
            user.avatar_url = user_info.get("picture") or user.avatar_url
            if user_info.get("email") and not user.email:
                user.email = user_info["email"]
            if user_info.get("email_verified"):
                user.is_verified = True

            # Update last login
            from datetime import datetime
            user.last_login_at = datetime.utcnow()

            await db.commit()
            await db.refresh(user)

            # Generate tokens
            access_token = create_access_token(
                data={"sub": str(user.id), "email": user.email}
            )
            refresh_token = create_refresh_token(
                data={"sub": str(user.id)}
            )

            logger.info(f"User logged in successfully via Google: {user.id} ({user.email})")

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth login failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication failed"
        )


async def _create_google_user(db, user_info: dict) -> User:
    """Create a new user from Google OAuth information."""
    import uuid
    from datetime import datetime

    # Generate username from name or email
    username = user_info.get("given_name")
    if not username and user_info.get("email"):
        username = user_info["email"].split("@")[0]
    if not username:
        username = f"user_{secrets.token_hex(4)}"

    # Check username uniqueness
    from sqlalchemy import select
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Add random suffix if username exists
        username = f"{username}_{secrets.token_hex(4)}"

    # Create user
    user = User(
        google_id=user_info["google_id"],
        email=user_info.get("email"),
        username=username,
        avatar_url=user_info.get("picture"),
        auth_provider=AuthProvider.GOOGLE,
        credits=settings.DEFAULT_USER_CREDITS,
        is_active=True,
        is_verified=user_info.get("email_verified", False),
        created_at=datetime.utcnow()
    )

    db.add(user)
    await db.flush()  # Flush to get user.id

    # Create initial credit transaction record
    from app.services.credits.manager import CreditManager
    from app.models.credit import TransactionType

    await CreditManager.add_credits(
        user_id=user.id,
        amount=settings.DEFAULT_USER_CREDITS,
        transaction_type=TransactionType.BONUS,
        reference_type="signup_bonus",
        reference_id=user.id,
        description="Welcome bonus - initial credits",
        db=db
    )

    logger.info(f"New user created via Google OAuth: {user.id} ({user.email})")

    return user


# SMS login removed - not needed (using Google OAuth only)


# Test login endpoint (development only)
@router.post("/test/login", response_model=TokenResponse)
async def test_login(email: str = "test@example.com"):
    """
    Test login endpoint - creates or logs in a test user.
    FOR DEVELOPMENT USE ONLY.
    """
    from app.db.base import get_db_write
    from app.models import User
    from sqlalchemy import select
    import uuid
    from datetime import datetime

    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test login not available in production"
        )

    try:
        async for db in get_db_write():
            # Check if test user exists
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                # Create test user
                user = User(
                    email=email,
                    username=email.split("@")[0],
                    auth_provider=AuthProvider.EMAIL,
                    credits=settings.DEFAULT_USER_CREDITS,
                    is_active=True,
                    is_verified=True,
                    created_at=datetime.utcnow()
                )

                db.add(user)
                await db.commit()
                await db.refresh(user)

                logger.info(f"Test user created: {user.id} ({email})")
            else:
                logger.info(f"Test user login: {user.id} ({email})")

            # Generate tokens
            access_token = create_access_token(
                data={"sub": str(user.id), "email": user.email}
            )
            refresh_token = create_refresh_token(
                data={"sub": str(user.id)}
            )

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )

    except Exception as e:
        logger.error(f"Test login failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Test login failed"
        )