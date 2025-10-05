"""
Database configuration with read-write separation support.
"""

from typing import Generator, Optional, List
import random
import os
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import select
import logging
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()


# Redis connection pool
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


class DatabaseManager:
    """
    Manages database connections with read-write separation.
    """

    def __init__(self):
        self.master_engine: Optional[AsyncEngine] = None
        self.slave_engines: List[AsyncEngine] = []
        self.master_session_factory: Optional[async_sessionmaker] = None
        self.slave_session_factories: List[async_sessionmaker] = []
        self._initialized = False

    async def initialize(self):
        """Initialize database connections."""
        if self._initialized:
            return

        # Detect serverless environment (Vercel, AWS Lambda, etc.)
        is_serverless = os.environ.get("VERCEL") == "1" or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")

        # Serverless-optimized configuration
        if is_serverless:
            logger.info("Serverless environment detected - using NullPool")

            # Create master (write) engine with NullPool for serverless
            self.master_engine = create_async_engine(
                settings.DATABASE_URL_MASTER,
                poolclass=NullPool,  # No connection pooling in serverless
                echo=settings.DATABASE_ECHO,
                connect_args={
                    "server_settings": {"jit": "off"},  # Disable JIT for faster cold starts
                    "command_timeout": 10,  # 10 second query timeout
                    "timeout": 10,  # 10 second connection timeout
                }
            )
        else:
            logger.info("Traditional environment detected - using connection pooling")

            # Create master (write) engine with connection pooling
            self.master_engine = create_async_engine(
                settings.DATABASE_URL_MASTER,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_timeout=settings.DATABASE_POOL_TIMEOUT,
                echo=settings.DATABASE_ECHO,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,  # Recycle connections after 1 hour
            )

        self.master_session_factory = async_sessionmaker(
            self.master_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,  # Prevent automatic flushing
        )

        # Create slave (read) engines
        slave_urls = settings.DATABASE_URL_SLAVES or [settings.DATABASE_URL_MASTER]
        for slave_url in slave_urls:
            if is_serverless:
                # Serverless configuration
                engine = create_async_engine(
                    slave_url,
                    poolclass=NullPool,
                    echo=settings.DATABASE_ECHO,
                    connect_args={
                        "server_settings": {"jit": "off"},
                        "command_timeout": 10,
                        "timeout": 10,
                    }
                )
            else:
                # Traditional configuration
                engine = create_async_engine(
                    slave_url,
                    pool_size=settings.DATABASE_POOL_SIZE // len(slave_urls),
                    max_overflow=settings.DATABASE_MAX_OVERFLOW // len(slave_urls),
                    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
                    echo=settings.DATABASE_ECHO,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                )
            self.slave_engines.append(engine)

            session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
            self.slave_session_factories.append(session_factory)

        self._initialized = True
        logger.info(f"Database initialized with 1 master and {len(self.slave_engines)} slave(s) in {'serverless' if is_serverless else 'traditional'} mode")

    async def close(self):
        """Close all database connections."""
        try:
            if self.master_engine:
                await self.master_engine.dispose()
                logger.debug("Master engine disposed")
        except Exception as e:
            logger.error(f"Error disposing master engine: {e}")

        for i, engine in enumerate(self.slave_engines):
            try:
                await engine.dispose()
                logger.debug(f"Slave engine {i} disposed")
            except Exception as e:
                logger.error(f"Error disposing slave engine {i}: {e}")

        self._initialized = False
        logger.info("Database connections closed")

    @asynccontextmanager
    async def get_master_session(self):
        """Get a session for write operations."""
        if not self._initialized:
            await self.initialize()

        session = None
        try:
            session = self.master_session_factory()
            yield session
            await session.commit()
        except Exception as e:
            if session:
                await session.rollback()
            logger.error(f"Error in master session: {e}")
            raise
        finally:
            if session:
                try:
                    await session.close()
                except Exception as e:
                    logger.warning(f"Error closing master session: {e}")

    @asynccontextmanager
    async def get_slave_session(self):
        """Get a session for read operations with load balancing."""
        if not self._initialized:
            await self.initialize()

        # Randomly select a slave for load balancing
        session_factory = random.choice(self.slave_session_factories)

        session = None
        try:
            session = session_factory()
            yield session
        except Exception as e:
            logger.error(f"Error in slave session: {e}")
            raise
        finally:
            if session:
                try:
                    await session.close()
                except Exception as e:
                    logger.warning(f"Error closing slave session: {e}")

    @asynccontextmanager
    async def get_session(self, read_only: bool = True):
        """
        Get a database session.

        Args:
            read_only: If True, returns a slave session for read operations.
                      If False, returns the master session for write operations.
        """
        if read_only:
            async with self.get_slave_session() as session:
                yield session
        else:
            async with self.get_master_session() as session:
                yield session

    async def execute_read(self, query):
        """Execute a read query on a slave database."""
        async with self.get_slave_session() as session:
            result = await session.execute(query)
            return result

    async def execute_write(self, query):
        """Execute a write query on the master database."""
        async with self.get_master_session() as session:
            result = await session.execute(query)
            await session.commit()
            return result

    async def health_check(self) -> dict:
        """Check the health of all database connections."""
        health_status = {
            "master": False,
            "slaves": []
        }

        # Check master
        try:
            async with self.get_master_session() as session:
                await session.execute(select(1))
                health_status["master"] = True
        except Exception as e:
            logger.error(f"Master database health check failed: {e}")

        # Check slaves
        for i, session_factory in enumerate(self.slave_session_factories):
            try:
                async with session_factory() as session:
                    await session.execute(select(1))
                    health_status["slaves"].append({"index": i, "status": True})
            except Exception as e:
                logger.error(f"Slave {i} database health check failed: {e}")
                health_status["slaves"].append({"index": i, "status": False})

        return health_status


# Global database manager instance
db_manager = DatabaseManager()


# Dependency injection functions for FastAPI
async def get_db_read() -> AsyncSession:
    """Dependency for read-only database operations."""
    async with db_manager.get_slave_session() as session:
        yield session


async def get_db_write() -> AsyncSession:
    """Dependency for write database operations."""
    async with db_manager.get_master_session() as session:
        yield session


async def get_db(read_only: bool = True) -> AsyncSession:
    """
    Generic dependency for database operations.

    Args:
        read_only: Whether the operation is read-only
    """
    async with db_manager.get_session(read_only=read_only) as session:
        yield session


# Redis Connection Management
async def initialize_redis(raise_on_error: bool = False):
    """
    Initialize Redis connection pool.

    Args:
        raise_on_error: If True, raises exception on failure.
                       If False, logs error and continues (graceful degradation)

    Raises:
        Exception: If raise_on_error is True and initialization fails
    """
    global _redis_pool, _redis_client

    if _redis_pool is None:
        try:
            _redis_pool = redis.ConnectionPool.from_url(
                settings.redis_dsn,
                max_connections=settings.REDIS_POOL_SIZE,
                decode_responses=settings.REDIS_DECODE_RESPONSES,
            )
            _redis_client = redis.Redis(connection_pool=_redis_pool)

            # Test connection
            await _redis_client.ping()
            logger.info("Redis connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            # Clean up partial initialization
            _redis_client = None
            _redis_pool = None

            if raise_on_error:
                raise
            else:
                logger.warning("Redis unavailable - features requiring Redis will be disabled")


async def close_redis():
    """Close Redis connection pool."""
    global _redis_pool, _redis_client

    if _redis_client:
        try:
            await _redis_client.close()
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")
        finally:
            _redis_client = None

    if _redis_pool:
        try:
            await _redis_pool.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting Redis pool: {e}")
        finally:
            _redis_pool = None

    logger.info("Redis connection closed")


async def redis_health_check() -> dict:
    """
    Check Redis connection health.

    Returns:
        Dictionary with health status and latency
    """
    global _redis_client

    if _redis_client is None:
        return {
            "status": "unavailable",
            "message": "Redis client not initialized"
        }

    try:
        import time
        start_time = time.time()
        await _redis_client.ping()
        latency_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2)
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def get_redis():
    """
    FastAPI dependency for Redis client.
    Yields Redis client for caching and session management.

    Yields:
        Redis client instance

    Raises:
        HTTPException: If Redis is not available and required
    """
    global _redis_client

    if _redis_client is None:
        try:
            await initialize_redis()
        except Exception as e:
            logger.error(f"Failed to get Redis client: {e}")
            # For graceful degradation, yield None and let the caller handle it
            # Alternatively, raise an exception if Redis is critical
            yield None
            return

    yield _redis_client