"""
Request utilities for handling client information.
"""
from fastapi import Request
from typing import Optional


def get_client_ip(request: Request) -> str:
    """
    Get real client IP address, considering Cloudflare proxy.

    Priority:
    1. request.state.real_ip (set by CloudflareMiddleware)
    2. CF-Connecting-IP header
    3. X-Forwarded-For header
    4. request.client.host

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # Try to get from request state (set by CloudflareMiddleware)
    if hasattr(request.state, "real_ip"):
        return request.state.real_ip

    # Fallback to headers
    return (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )


def get_cloudflare_info(request: Request) -> dict:
    """
    Get Cloudflare request information.

    Args:
        request: FastAPI request object

    Returns:
        dict: {
            'ray': Cloudflare Ray ID (unique request identifier),
            'country': Country code (e.g., 'US', 'CN'),
            'colo': Datacenter code (e.g., 'HKG', 'LAX'),
            'ip': Client IP address,
            'is_cloudflare': Whether request came through Cloudflare
        }
    """
    # Try to get from request state (set by CloudflareMiddleware)
    if hasattr(request.state, "cf_info"):
        return {**request.state.cf_info, "is_cloudflare": True}

    # Fallback to headers
    cf_ray = request.headers.get("CF-Ray")
    is_cloudflare = cf_ray is not None

    return {
        "ray": cf_ray,
        "country": request.headers.get("CF-IPCountry"),
        "colo": cf_ray.split("-")[-1] if cf_ray else None,
        "ip": get_client_ip(request),
        "is_cloudflare": is_cloudflare,
    }


def get_user_agent(request: Request) -> Optional[str]:
    """
    Get User-Agent string from request.

    Args:
        request: FastAPI request object

    Returns:
        User-Agent string or None
    """
    return request.headers.get("User-Agent")


def is_mobile_device(request: Request) -> bool:
    """
    Check if request is from a mobile device.

    Args:
        request: FastAPI request object

    Returns:
        True if mobile device, False otherwise
    """
    user_agent = get_user_agent(request)
    if not user_agent:
        return False

    user_agent_lower = user_agent.lower()
    mobile_keywords = ["mobile", "android", "iphone", "ipad", "tablet", "webos"]

    return any(keyword in user_agent_lower for keyword in mobile_keywords)


def get_request_info(request: Request) -> dict:
    """
    Get comprehensive request information.

    Args:
        request: FastAPI request object

    Returns:
        dict with request details
    """
    cf_info = get_cloudflare_info(request)

    return {
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "ip": cf_info["ip"],
        "user_agent": get_user_agent(request),
        "is_mobile": is_mobile_device(request),
        "cloudflare": cf_info,
    }
