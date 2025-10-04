"""
Region detection middleware for routing users to appropriate services.
"""

import logging
from typing import Optional, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Optional geoip2 import
try:
    import geoip2.database
    import geoip2.errors
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False
    logger.warning("geoip2 not installed. Region detection from IP will be disabled. Install with: pip install geoip2")


class RegionDetectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to detect user's region and add it to request state.
    """

    def __init__(self, app, geoip_db_path: Optional[Path] = None):
        super().__init__(app)
        self.geoip_reader = None

        # Initialize GeoIP database if available
        if GEOIP2_AVAILABLE:
            db_path = geoip_db_path or settings.GEOIP_DATABASE_PATH
            if db_path and db_path.exists():
                try:
                    self.geoip_reader = geoip2.database.Reader(str(db_path))
                    logger.info(f"GeoIP database loaded from {db_path}")
                except Exception as e:
                    logger.warning(f"Failed to load GeoIP database: {e}")
            else:
                logger.info(f"GeoIP database not found at {db_path}. IP-based region detection disabled.")

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and add region information.
        """
        # Detect region
        region, country = self.detect_region(request)

        # Add to request state
        request.state.region = region
        request.state.country = country
        request.state.is_china_region = region == "CN"

        # Add region headers to response
        response = await call_next(request)
        response.headers["X-User-Region"] = region
        response.headers["X-User-Country"] = country or "Unknown"

        return response

    def detect_region(self, request: Request) -> Tuple[str, Optional[str]]:
        """
        Detect user's region from various sources.

        Args:
            request: The incoming request

        Returns:
            Tuple of (region_code, country_code)
        """
        # 1. Check if region is explicitly set in headers (for testing or override)
        override_region = request.headers.get("X-Override-Region")
        if override_region and override_region in settings.SUPPORTED_REGIONS:
            logger.debug(f"Using override region: {override_region}")
            return override_region, override_region

        # 2. Check if user has a stored preference (from cookies/session)
        region_cookie = request.cookies.get("user_region")
        if region_cookie and region_cookie in settings.SUPPORTED_REGIONS:
            logger.debug(f"Using cookie region: {region_cookie}")
            return region_cookie, region_cookie

        # 3. Detect from IP address
        client_ip = self.get_client_ip(request)
        if client_ip and self.geoip_reader and GEOIP2_AVAILABLE:
            try:
                response = self.geoip_reader.city(client_ip)
                country_code = response.country.iso_code

                # Map country to region
                region = self.map_country_to_region(country_code)
                logger.debug(f"Detected region {region} for IP {client_ip} (Country: {country_code})")
                return region, country_code

            except Exception as e:
                if GEOIP2_AVAILABLE:
                    # Only log specific geoip2 errors if library is available
                    try:
                        if isinstance(e, geoip2.errors.AddressNotFoundError):
                            logger.debug(f"IP {client_ip} not found in GeoIP database")
                        else:
                            logger.error(f"GeoIP lookup failed for {client_ip}: {e}")
                    except:
                        logger.error(f"GeoIP lookup failed for {client_ip}: {e}")
                else:
                    logger.error(f"GeoIP lookup failed for {client_ip}: {e}")

        # 4. Check Accept-Language header as fallback
        accept_language = request.headers.get("Accept-Language", "")
        if "zh" in accept_language.lower():
            logger.debug("Detected Chinese from Accept-Language header")
            return "CN", "CN"

        # 5. Default region
        logger.debug(f"Using default region: {settings.DEFAULT_REGION}")
        return settings.DEFAULT_REGION, None

    def get_client_ip(self, request: Request) -> Optional[str]:
        """
        Get the real client IP address.

        Args:
            request: The incoming request

        Returns:
            Client IP address or None
        """
        # Check various headers for the real IP (when behind proxy/load balancer)
        headers_to_check = [
            "X-Real-IP",
            "X-Forwarded-For",
            "CF-Connecting-IP",  # Cloudflare
            "True-Client-IP",    # Cloudflare Enterprise
            "X-Client-IP",
        ]

        for header in headers_to_check:
            ip = request.headers.get(header)
            if ip:
                # X-Forwarded-For can contain multiple IPs
                if "," in ip:
                    ip = ip.split(",")[0].strip()
                return ip

        # Fall back to request client host
        if request.client and request.client.host:
            return request.client.host

        return None

    def map_country_to_region(self, country_code: str) -> str:
        """
        Map country code to region.

        Args:
            country_code: ISO country code

        Returns:
            Region identifier
        """
        # China region
        if country_code in ["CN", "HK", "MO", "TW"]:
            return "CN"

        # Asia region
        elif country_code in ["JP", "KR", "SG", "MY", "TH", "ID", "PH", "VN", "IN"]:
            return "ASIA"

        # Europe region
        elif country_code in [
            "GB", "DE", "FR", "IT", "ES", "NL", "BE", "CH", "AT", "SE",
            "NO", "DK", "FI", "PL", "CZ", "PT", "GR", "IE", "RO", "HU"
        ]:
            return "EU"

        # US and Americas
        elif country_code in ["US", "CA", "MX", "BR", "AR", "CL", "CO", "PE"]:
            return "US"

        # Default to US region for all others
        else:
            return "US"

    def __del__(self):
        """Clean up GeoIP reader."""
        if self.geoip_reader:
            self.geoip_reader.close()


def get_user_region(request: Request) -> str:
    """
    Get user's region from request state.

    Args:
        request: FastAPI request object

    Returns:
        Region code
    """
    return getattr(request.state, "region", settings.DEFAULT_REGION)


def is_china_region(request: Request) -> bool:
    """
    Check if user is in China region.

    Args:
        request: FastAPI request object

    Returns:
        True if user is in China region
    """
    return getattr(request.state, "is_china_region", False)