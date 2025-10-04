"""
Common dependencies for FastAPI endpoints.
"""

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.base import get_db_read, get_db_write
from sqlalchemy.ext.asyncio import AsyncSession

# Alias for backward compatibility
get_db = get_db_write

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """
    Verify API key for service-to-service authentication.

    Args:
        x_api_key: API key from header

    Returns:
        The API key if valid

    Raises:
        HTTPException: If API key is invalid
    """
    if not settings.PROXY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured"
        )

    if x_api_key != settings.PROXY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return x_api_key


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_read)
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        User information dictionary

    Raises:
        HTTPException: If token is invalid or user not found
    """
    from app.models import User
    from sqlalchemy import select

    token = credentials.credentials

    try:
        # Decode JWT token
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Query user from database
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user_model = result.scalar_one_or_none()

        if not user_model:
            logger.error(f"User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is deleted (soft delete)
        if user_model.is_deleted:
            logger.error(f"User is deleted: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account has been deleted",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Convert to dictionary for easier access
        user = {
            "id": user_model.id,
            "email": user_model.email,
            "username": user_model.username,
            "avatar_url": user_model.avatar_url,
            "region": user_model.region.value if user_model.region else "US",
            "credits": user_model.credits,
            "is_active": user_model.is_active,
            "is_superuser": user_model.is_superuser,
            "is_verified": user_model.is_verified,
            "auth_provider": user_model.auth_provider.value if user_model.auth_provider else None,
            "created_at": user_model.created_at.isoformat() if user_model.created_at else None,
            "last_login_at": user_model.last_login_at.isoformat() if user_model.last_login_at else None
        }

        logger.info(f"User authenticated: {user_id}")
        return user

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current active user.

    Args:
        current_user: Current user from JWT

    Returns:
        Active user information

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_superuser(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get current superuser.

    Args:
        current_user: Current active user

    Returns:
        Superuser information

    Raises:
        HTTPException: If user is not superuser
    """
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


class RateLimitDependency:
    """Rate limiting dependency using Redis sliding window algorithm."""

    def __init__(self, calls: int = 100, period: int = 60):
        """
        Initialize rate limiter.

        Args:
            calls: Number of calls allowed
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period

    async def __call__(
        self,
        request,
        current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
    ):
        """
        Check rate limit for user using Redis sliding window algorithm.

        Args:
            request: FastAPI request object
            current_user: Current authenticated user

        Raises:
            HTTPException: If rate limit is exceeded
        """
        from app.db.base import get_redis

        # Skip rate limiting if disabled
        if not settings.RATE_LIMIT_ENABLED:
            return

        try:
            import time

            # Get Redis client from the connection pool
            redis_client = None
            async for client in get_redis():
                redis_client = client
                break

            # If Redis is unavailable, log and allow request (fail open)
            if redis_client is None:
                logger.warning("Redis unavailable - rate limiting disabled")
                return

            # Determine rate limit key (prefer user_id, fallback to IP)
            if current_user and current_user.get("id"):
                rate_limit_key = f"rate_limit:user:{current_user['id']}"
            else:
                client_ip = request.client.host if request.client else "unknown"
                rate_limit_key = f"rate_limit:ip:{client_ip}"

            # Add endpoint to key for more granular control
            endpoint = f"{request.method}:{request.url.path}"
            rate_limit_key = f"{rate_limit_key}:{endpoint}"

            # Current timestamp
            current_time = time.time()
            window_start = current_time - self.period

            # Use Redis sorted set for sliding window
            # Add current request with score as timestamp
            await redis_client.zadd(rate_limit_key, {str(current_time): current_time})

            # Remove old entries outside the time window
            await redis_client.zremrangebyscore(rate_limit_key, 0, window_start)

            # Count requests in current window
            request_count = await redis_client.zcard(rate_limit_key)

            # Set expiration on the key
            await redis_client.expire(rate_limit_key, self.period + 1)

            # Check if rate limit exceeded
            if request_count > self.calls:
                logger.warning(
                    f"Rate limit exceeded for {rate_limit_key}: "
                    f"{request_count}/{self.calls} in {self.period}s"
                )

                # Calculate retry after time
                # Get the oldest request in the window
                oldest_requests = await redis_client.zrange(
                    rate_limit_key, 0, 0, withscores=True
                )
                if oldest_requests:
                    oldest_time = oldest_requests[0][1]
                    retry_after = int(oldest_time + self.period - current_time) + 1
                else:
                    retry_after = self.period

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {self.calls} requests per {self.period} seconds.",
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.calls),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(current_time + retry_after))
                    }
                )

            # Add rate limit headers to response
            remaining = self.calls - request_count
            logger.debug(
                f"Rate limit check passed for {rate_limit_key}: "
                f"{request_count}/{self.calls} requests"
            )

            # Store rate limit info in request state for response headers
            request.state.rate_limit_limit = self.calls
            request.state.rate_limit_remaining = remaining
            request.state.rate_limit_reset = int(current_time + self.period)

        except HTTPException:
            # Re-raise rate limit exceptions
            raise
        except Exception as e:
            # Log error but don't block request if Redis fails
            logger.error(f"Rate limiting error: {e}", exc_info=True)
            # Fail open - allow request when Redis has issues
            # This ensures service availability even when Redis is down
            logger.warning("Rate limiting bypassed due to Redis error - allowing request")
            pass


# Common dependencies for endpoints
rate_limit_100_per_minute = RateLimitDependency(calls=100, period=60)
rate_limit_10_per_minute = RateLimitDependency(calls=10, period=60)