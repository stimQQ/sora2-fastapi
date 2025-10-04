"""
SMS service for sending verification codes using Aliyun SMS API.
"""

import logging
import secrets
from typing import Optional
from datetime import timedelta

from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
from alibabacloud_tea_util import models as util_models

from app.core.config import settings

logger = logging.getLogger(__name__)


class SMSService:
    """Aliyun SMS service for verification codes."""

    def __init__(self):
        """Initialize Aliyun SMS client."""
        # Create configuration
        config = open_api_models.Config(
            access_key_id=settings.ALIYUN_SMS_ACCESS_KEY,
            access_key_secret=settings.ALIYUN_SMS_SECRET_KEY,
        )
        # Set endpoint
        config.endpoint = 'dysmsapi.aliyuncs.com'

        # Create client
        self.client = DysmsapiClient(config)

    def generate_verification_code(self, length: int = 6) -> str:
        """
        Generate a numeric verification code.

        Args:
            length: Length of the code (default 6)

        Returns:
            Numeric verification code as string
        """
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])

    async def send_verification_code(
        self,
        phone_number: str,
        code: str,
        template_code: Optional[str] = None,
    ) -> dict:
        """
        Send SMS verification code to phone number.

        Args:
            phone_number: Phone number to send SMS to (e.g., "86-13800138000")
            code: Verification code to send
            template_code: Aliyun SMS template code (uses default if not provided)

        Returns:
            Response dict with success status and message

        Raises:
            Exception: If SMS sending fails
        """
        # Use default template if not provided
        if not template_code:
            template_code = settings.ALIYUN_SMS_TEMPLATE_CODE

        # Parse phone number (format: country_code-phone_number)
        if '-' in phone_number:
            country_code, phone = phone_number.split('-', 1)
        else:
            # Default to China if no country code
            country_code = '86'
            phone = phone_number

        try:
            # Create request
            request = dysmsapi_models.SendSmsRequest(
                phone_numbers=phone,
                sign_name=settings.ALIYUN_SMS_SIGN_NAME,
                template_code=template_code,
                template_param=f'{{"code":"{code}"}}',  # JSON string with code parameter
            )

            # Runtime options
            runtime = util_models.RuntimeOptions()

            # Send SMS
            response = self.client.send_sms_with_options(request, runtime)

            # Check response
            if response.body.code == 'OK':
                logger.info(f"SMS sent successfully to {phone_number}")
                return {
                    "success": True,
                    "message": "Verification code sent successfully",
                    "request_id": response.body.request_id,
                }
            else:
                logger.error(f"SMS sending failed: {response.body.code} - {response.body.message}")
                return {
                    "success": False,
                    "message": f"Failed to send SMS: {response.body.message}",
                    "code": response.body.code,
                }

        except Exception as e:
            logger.error(f"Error sending SMS to {phone_number}: {e}", exc_info=True)
            raise Exception(f"Failed to send SMS: {str(e)}")

    async def store_verification_code(
        self,
        redis_client,
        phone_number: str,
        code: str,
        expire_minutes: int = 5,
    ):
        """
        Store verification code in Redis with expiration.

        Args:
            redis_client: Redis client instance
            phone_number: Phone number
            code: Verification code
            expire_minutes: Expiration time in minutes (default 5)

        Raises:
            Exception: If Redis operation fails
        """
        try:
            key = f"sms:verification:{phone_number}"
            await redis_client.setex(
                key,
                timedelta(minutes=expire_minutes),
                code
            )
            logger.info(f"Stored verification code for {phone_number} (expires in {expire_minutes} min)")
        except Exception as e:
            logger.error(f"Failed to store verification code in Redis: {e}", exc_info=True)
            raise Exception(f"Failed to store verification code: {str(e)}")

    async def verify_code(
        self,
        redis_client,
        phone_number: str,
        code: str,
    ) -> bool:
        """
        Verify SMS verification code.

        Args:
            redis_client: Redis client instance
            phone_number: Phone number
            code: Verification code to verify

        Returns:
            True if code is valid, False otherwise

        Raises:
            Exception: If Redis operation fails
        """
        try:
            key = f"sms:verification:{phone_number}"
            stored_code = await redis_client.get(key)

            if not stored_code:
                logger.warning(f"No verification code found for {phone_number}")
                return False

            # Compare codes (Redis returns string if decode_responses=True, bytes otherwise)
            stored_code_str = stored_code if isinstance(stored_code, str) else stored_code.decode('utf-8')

            if stored_code_str == code:
                # Delete code after successful verification
                await redis_client.delete(key)
                logger.info(f"Verification successful for {phone_number}")
                return True
            else:
                logger.warning(f"Invalid verification code for {phone_number}")
                return False
        except Exception as e:
            logger.error(f"Failed to verify code in Redis: {e}", exc_info=True)
            raise Exception(f"Failed to verify code: {str(e)}")

    async def check_rate_limit(
        self,
        redis_client,
        phone_number: str,
        max_requests: int = 5,
        window_minutes: int = 60,
    ) -> tuple[bool, int]:
        """
        Check rate limit for sending SMS to a phone number.

        Args:
            redis_client: Redis client instance
            phone_number: Phone number
            max_requests: Maximum number of requests allowed
            window_minutes: Time window in minutes

        Returns:
            Tuple of (is_allowed, remaining_requests)

        Raises:
            Exception: If Redis operation fails
        """
        try:
            key = f"sms:ratelimit:{phone_number}"

            # Increment counter
            count = await redis_client.incr(key)

            # Set expiration on first request
            if count == 1:
                await redis_client.expire(key, timedelta(minutes=window_minutes))

            remaining = max(0, max_requests - count)
            is_allowed = count <= max_requests

            if not is_allowed:
                logger.warning(f"Rate limit exceeded for {phone_number}: {count}/{max_requests}")

            return is_allowed, remaining
        except Exception as e:
            logger.error(f"Failed to check rate limit in Redis: {e}", exc_info=True)
            raise Exception(f"Failed to check rate limit: {str(e)}")


# Create singleton instance
sms_service = SMSService()
