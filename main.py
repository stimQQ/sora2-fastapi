"""
Main FastAPI application entry point.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import application modules
from app.core.config import settings
from app.db.base import db_manager, initialize_redis, close_redis, redis_health_check
from app.middleware.region import RegionDetectionMiddleware
from app.middleware.cloudflare import CloudflareMiddleware
from app.api.router import api_router
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting up Video Animation Platform...")

    # Initialize database
    await db_manager.initialize()

    # Check database health
    health = await db_manager.health_check()
    logger.info(f"Database health: {health}")

    # Initialize Redis
    try:
        await initialize_redis()
    except Exception as e:
        logger.warning(f"Redis initialization failed: {e}. Some features may be unavailable.")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Close Redis connections
    await close_redis()

    # Close database connections
    await db_manager.close()

    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered video animation generation platform with global reach",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
allowed_origins = settings.cors_origins if settings.cors_origins else ["*"]
logger.info(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Cloudflare middleware (must be added before other middlewares)
app.add_middleware(CloudflareMiddleware)

# Add region detection middleware
app.add_middleware(RegionDetectionMiddleware)

# Include API routers
app.include_router(api_router)


# Root endpoint
@app.get("/")
async def root(request: Request):
    """Root endpoint with API information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "region": getattr(request.state, "region", "Unknown"),
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
        },
        "endpoints": {
            "base": "/api",
            "auth": "/api/auth",
            "tasks": "/api/tasks",
            "videos": "/api/videos",
            "payments": "/api/payments",
            "users": "/api/users",
        }
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    Checks database and Redis connectivity.
    """
    # Check database health
    db_health = await db_manager.health_check()

    # Check Redis health
    redis_health = await redis_health_check()

    # Overall health status
    # Service is healthy if database master is up (Redis is optional)
    is_healthy = db_health["master"] and any(slave["status"] for slave in db_health.get("slaves", []))

    # Add warning if Redis is unavailable but database is healthy
    if is_healthy and redis_health.get("status") != "healthy":
        status_message = "degraded"
    elif is_healthy:
        status_message = "healthy"
    else:
        status_message = "unhealthy"

    return {
        "status": status_message,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_health,
        "redis": redis_health,
    }


# Metrics endpoint (if Prometheus is enabled)
if settings.PROMETHEUS_ENABLED:
    from prometheus_client import make_asgi_app
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Don't expose internal errors in production
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)