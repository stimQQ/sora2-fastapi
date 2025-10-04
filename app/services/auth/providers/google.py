"""
Google OAuth authentication provider.
"""

import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlencode
import logging

from app.services.auth.base import AuthProvider, AuthUserInfo
from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleProvider(AuthProvider):
    """Google OAuth2.0 authentication provider."""

    OAUTH_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})
        self.client_id = config.get("client_id") or settings.GOOGLE_CLIENT_ID
        self.client_secret = config.get("client_secret") or settings.GOOGLE_CLIENT_SECRET

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """
        Get Google OAuth authorization URL.

        Args:
            state: State parameter for CSRF protection
            redirect_uri: Callback URL

        Returns:
            Google authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",  # To get refresh token
            "prompt": "select_account",  # Force account selection
        }

        return f"{self.OAUTH_BASE_URL}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from Google
            redirect_uri: Callback URL (must match the one used in authorization)

        Returns:
            Token information including access_token
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
            token_data = response.json()

            if "error" in token_data:
                logger.error(f"Google token exchange failed: {token_data}")
                raise Exception(f"Google OAuth error: {token_data.get('error_description', token_data.get('error'))}")

            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "id_token": token_data.get("id_token"),
                "token_type": token_data.get("token_type", "Bearer"),
                "expires_in": token_data.get("expires_in", 3600),
                "scope": token_data.get("scope"),
            }

    async def get_user_info(self, access_token: str) -> AuthUserInfo:
        """
        Get user information from Google.

        Args:
            access_token: Google access token

        Returns:
            Standardized user information
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.USER_INFO_URL, headers=headers)

            if response.status_code != 200:
                logger.error(f"Google get user info failed: {response.text}")
                raise Exception(f"Failed to get Google user info: {response.status_code}")

            data = response.json()

            return AuthUserInfo(
                provider="google",
                provider_user_id=data["id"],
                email=data.get("email"),
                nickname=data.get("name"),
                avatar=data.get("picture"),
                raw_data=data,
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh Google access token.

        Args:
            refresh_token: Google refresh token

        Returns:
            New token information
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
            token_data = response.json()

            if "error" in token_data:
                logger.error(f"Google token refresh failed: {token_data}")
                raise Exception(f"Google refresh error: {token_data.get('error_description', token_data.get('error'))}")

            return {
                "access_token": token_data["access_token"],
                "token_type": token_data.get("token_type", "Bearer"),
                "expires_in": token_data.get("expires_in", 3600),
                "scope": token_data.get("scope"),
            }

    async def revoke_token(self, access_token: str) -> bool:
        """
        Revoke a Google access token.

        Args:
            access_token: Token to revoke

        Returns:
            True if successful
        """
        params = {
            "token": access_token,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.REVOKE_URL, params=params)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Google token revocation failed: {e}")
            return False

    async def validate_token(self, access_token: str) -> bool:
        """
        Validate if a Google token is still valid.

        Args:
            access_token: Token to validate

        Returns:
            True if valid
        """
        try:
            user_info = await self.get_user_info(access_token)
            return user_info is not None
        except Exception as e:
            logger.debug(f"Google token validation failed: {e}")
            return False