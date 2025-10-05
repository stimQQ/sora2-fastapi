"""
Vercel serverless entry point for FastAPI application.
This module adapts the FastAPI app to work in Vercel's serverless environment.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Set Vercel environment flag BEFORE any imports
os.environ["VERCEL"] = "1"

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

# Import application modules
from app.core.config import settings
from app.middleware.cloudflare import CloudflareMiddleware
from app.api.router import api_router
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI application WITHOUT lifespan for serverless
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered video animation generation platform - Serverless API",
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

# Add Cloudflare middleware (works well in Vercel behind Cloudflare)
app.add_middleware(CloudflareMiddleware)

# NOTE: Region detection middleware is removed for serverless
# GeoIP database files are too large for serverless bundles
# Use Cloudflare headers (CF-IPCountry) for region detection instead

# Include API routers
app.include_router(api_router)


@app.get("/")
async def root(request: Request):
    """Root endpoint with API information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "platform": "Vercel Serverless",
        "region": request.headers.get("CF-IPCountry", "Unknown"),
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


@app.get("/health")
async def health_check():
    """
    Simplified health check for serverless environment.
    Database and Redis connections are checked on-demand, not at startup.
    """
    from app.db.base import db_manager

    # Initialize DB if needed (serverless lazy initialization)
    if not db_manager._initialized:
        try:
            await db_manager.initialize()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return {
                "status": "unhealthy",
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "platform": "Vercel Serverless",
                "error": str(e)
            }

    # Check database health
    try:
        db_health = await db_manager.health_check()
        is_healthy = db_health["master"]
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "platform": "Vercel Serverless",
            "error": str(e)
        }

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "platform": "Vercel Serverless",
        "database": db_health,
        "note": "Redis and Celery run externally in serverless mode"
    }


@app.get("/api/health")
async def api_health_check():
    """Alternative health endpoint at /api/health."""
    return await health_check()


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
            content={
                "detail": "Internal server error",
                "platform": "Vercel Serverless"
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "platform": "Vercel Serverless"
            }
        )


# Request context middleware for serverless
@app.middleware("http")
async def add_serverless_context(request: Request, call_next):
    """Add serverless-specific context to requests."""
    # Get region from Cloudflare headers (more reliable in Vercel)
    region = request.headers.get("CF-IPCountry", settings.DEFAULT_REGION)
    request.state.region = region
    request.state.country = region
    request.state.is_china_region = region == "CN"

    response = await call_next(request)

    # Add serverless headers
    response.headers["X-Serverless-Platform"] = "Vercel"
    response.headers["X-User-Region"] = region

    return response


# Vercel expects a variable named 'app'
# This is the ASGI application that Vercel will invoke
handler = app
