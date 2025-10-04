"""
Cloudflare middleware for getting real client IP and request info.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class CloudflareMiddleware(BaseHTTPMiddleware):
    """
    Extract real client IP from Cloudflare headers.

    Cloudflare adds the following headers:
    - CF-Connecting-IP: Real client IP
    - CF-Ray: Unique request identifier
    - CF-IPCountry: Client country code
    - CF-Visitor: Connection scheme (http/https)
    """

    async def dispatch(self, request: Request, call_next):
        # Get real IP from Cloudflare headers
        real_ip = (
            request.headers.get("CF-Connecting-IP")
            or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )

        # Store real IP in request state
        request.state.real_ip = real_ip

        # Get Cloudflare info
        cf_ray = request.headers.get("CF-Ray")
        cf_country = request.headers.get("CF-IPCountry")
        cf_colo = cf_ray.split("-")[-1] if cf_ray else None  # Datacenter code

        # Store Cloudflare info in request state
        request.state.cf_info = {
            "ray": cf_ray,
            "country": cf_country,
            "colo": cf_colo,
            "ip": real_ip,
        }

        # Log Cloudflare request info (debug level)
        if cf_ray:
            logger.debug(
                f"Cloudflare request: Ray={cf_ray}, IP={real_ip}, "
                f"Country={cf_country}, Datacenter={cf_colo}"
            )

        # Process request
        response = await call_next(request)

        # Add Cloudflare info to response headers (optional, for debugging)
        if cf_ray:
            response.headers["X-CF-Ray"] = cf_ray

        return response
