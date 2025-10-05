"""
Vercel serverless entry point.
Creates a simplified FastAPI app for serverless environment.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Set environment variable to skip directory creation in config
os.environ.setdefault('VERCEL', '1')

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import application modules
from app.core.config import settings
from app.middleware.region import RegionDetectionMiddleware
from app.middleware.cloudflare import CloudflareMiddleware
from app.api.router import api_router

# Create FastAPI application (without lifespan for serverless)
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered video animation generation platform with global reach",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
allowed_origins = settings.cors_origins if settings.cors_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Cloudflare middleware
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
        "platform": "Vercel Serverless",
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
            "showcase": "/api/showcase",
        }
    }


# Health check endpoint (simplified for serverless)
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "platform": "Vercel Serverless",
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
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


# Create Mangum handler for Vercel
handler = Mangum(app, lifespan="off")
