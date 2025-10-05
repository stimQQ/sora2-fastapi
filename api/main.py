"""
Vercel serverless entry point.
Creates a simplified FastAPI app for serverless environment.
"""
import sys
import os
from pathlib import Path

# Setup Python path FIRST before any imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure environment
os.environ.update({
    "VERCEL": "1",
    "DISABLE_REDIS": "1"
})

# Use direct print statements for critical info
print("="*60, flush=True)
print("[VERCEL] Serverless Entry Point Starting", flush=True)
print(f"[VERCEL] Python path: {sys.path[0]}", flush=True)
print(f"[VERCEL] Current directory: {os.getcwd()}", flush=True)
print(f"[VERCEL] Environment: {os.environ.get('VERCEL')}", flush=True)
print("="*60, flush=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import application modules
from app.core.config import settings
from app.middleware.region import RegionDetectionMiddleware
from app.middleware.cloudflare import CloudflareMiddleware
from app.api.router import api_router

print("[VERCEL] ✓ Successfully imported all modules", flush=True)

# Create FastAPI application (without lifespan for serverless)
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered video animation generation platform with global reach",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS - Critical for handling OPTIONS preflight requests
allowed_origins = settings.cors_origins if settings.cors_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Add Cloudflare middleware
app.add_middleware(CloudflareMiddleware)

# Add region detection middleware
app.add_middleware(RegionDetectionMiddleware)

# Include API routers
app.include_router(api_router)


# Global OPTIONS handler for CORS preflight
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle OPTIONS preflight requests for CORS."""
    return JSONResponse(
        status_code=200,
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
        }
    )


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


# Vercel ASGI Handler
# Vercel requires the handler to be a callable ASGI application
# The 'app' variable is already the FastAPI instance which is ASGI-compatible
# No need for Mangum - Vercel can directly use FastAPI as ASGI app

print("[VERCEL] ✓ FastAPI app created and ready", flush=True)
print(f"[VERCEL] App title: {app.title}", flush=True)
print(f"[VERCEL] Routes count: {len(app.routes)}", flush=True)
