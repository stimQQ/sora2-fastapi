"""
Google OAuth authentication provider.
"""

import logging
from typing import Optional, Dict, Any
from google.oauth2 import id_token
from google.auth.transport import requests
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleOAuthProvider:
    """Google OAuth provider for user authentication."""

    def __init__(self):
        """Initialize Google OAuth provider."""
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"

    async def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from Google OAuth
            redirect_uri: Optional redirect URI (defaults to configured value)

        Returns:
            Dictionary containing access_token, id_token, etc.

        Raises:
            Exception: If token exchange fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_endpoint,
                    data={
                        "code": code,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uri": redirect_uri or self.redirect_uri,
                        "grant_type": "authorization_code",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"Google token exchange failed: {response.text}")
                    raise Exception(f"Failed to exchange code for token: {response.text}")

                token_data = response.json()
                logger.info("Successfully exchanged code for Google access token")
                return token_data

        except Exception as e:
            logger.error(f"Error exchanging Google code for token: {e}")
            raise

    async def verify_id_token(self, id_token_str: str) -> Dict[str, Any]:
        """
        Verify Google ID token and extract user information.

        Args:
            id_token_str: ID token string from Google

        Returns:
            Dictionary containing user information

        Raises:
            Exception: If token verification fails
        """
        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                requests.Request(),
                self.client_id
            )

            # Verify the issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Invalid token issuer')

            # Extract user information
            user_info = {
                "google_id": idinfo['sub'],
                "email": idinfo.get('email'),
                "email_verified": idinfo.get('email_verified', False),
                "name": idinfo.get('name'),
                "given_name": idinfo.get('given_name'),
                "family_name": idinfo.get('family_name'),
                "picture": idinfo.get('picture'),
                "locale": idinfo.get('locale', 'en'),
            }

            logger.info(f"Successfully verified Google ID token for user: {user_info['email']}")
            return user_info

        except ValueError as e:
            logger.error(f"Invalid Google ID token: {e}")
            raise Exception(f"Invalid ID token: {str(e)}")
        except Exception as e:
            logger.error(f"Error verifying Google ID token: {e}")
            raise

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information using access token.

        Args:
            access_token: Google access token

        Returns:
            Dictionary containing user information

        Raises:
            Exception: If user info retrieval fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if response.status_code != 200:
                    logger.error(f"Failed to get Google user info: {response.text}")
                    raise Exception(f"Failed to get user info: {response.text}")

                user_info = response.json()
                logger.info(f"Successfully retrieved Google user info for: {user_info.get('email')}")
                return user_info

        except Exception as e:
            logger.error(f"Error getting Google user info: {e}")
            raise

    async def authenticate(self, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete Google OAuth authentication flow.

        Args:
            code: Authorization code from Google
            redirect_uri: Optional redirect URI (defaults to configured value)

        Returns:
            Dictionary containing user information

        Raises:
            Exception: If authentication fails
        """
        try:
            # Exchange code for tokens
            token_data = await self.exchange_code_for_token(code, redirect_uri)

            # Verify ID token and extract user info
            if "id_token" in token_data:
                user_info = await self.verify_id_token(token_data["id_token"])
            else:
                # Fallback: get user info using access token
                user_info = await self.get_user_info(token_data["access_token"])
                # Add google_id from sub field if available
                if "id" in user_info:
                    user_info["google_id"] = user_info["id"]

            return user_info

        except Exception as e:
            logger.error(f"Google authentication failed: {e}")
            raise


# Create singleton instance
google_oauth_provider = GoogleOAuthProvider()
