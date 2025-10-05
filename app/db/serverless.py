"""
Serverless-optimized database utilities.
Provides helpers for serverless environments like Vercel.
"""

from typing import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from app.db.base import db_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_serverless_db_session(read_only: bool = True) -> AsyncGenerator:
    """
    Get database session optimized for serverless environments.
    Automatically initializes DB on first call (lazy initialization).

    Args:
        read_only: If True, returns a slave session for read operations.

    Yields:
        AsyncSession: Database session
    """
    # Lazy initialization for serverless
    if not db_manager._initialized:
        logger.info("Initializing database for serverless request")
        await db_manager.initialize()

    # Use the appropriate session
    async with db_manager.get_session(read_only=read_only) as session:
        yield session


async def serverless_db_dependency(read_only: bool = True):
    """
    FastAPI dependency for serverless database sessions.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(serverless_db_read)):
            ...
    """
    async with get_serverless_db_session(read_only=read_only) as session:
        yield session


async def serverless_db_read():
    """Serverless dependency for read-only operations."""
    async for session in serverless_db_dependency(read_only=True):
        yield session


async def serverless_db_write():
    """Serverless dependency for write operations."""
    async for session in serverless_db_dependency(read_only=False):
        yield session
