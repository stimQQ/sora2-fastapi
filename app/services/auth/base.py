"""
Base authentication provider interface.
All authentication providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class AuthUserInfo(BaseModel):
    """Standard user information returned by auth providers."""
    provider: str
    provider_user_id: str
    email: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    phone: Optional[str] = None
    raw_data: Dict[str, Any] = {}


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the auth provider with configuration.

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.provider_name = self.__class__.__name__.lower().replace('provider', '')

    @abstractmethod
    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """
        Get the authorization URL for OAuth flow.

        Args:
            state: State parameter for CSRF protection
            redirect_uri: Callback URL

        Returns:
            Authorization URL
        """
        pass

    @abstractmethod
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code
            redirect_uri: Callback URL

        Returns:
            Token information including access_token
        """
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> AuthUserInfo:
        """
        Get user information using access token.

        Args:
            access_token: OAuth access token

        Returns:
            Standardized user information
        """
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh the access token using refresh token.

        Args:
            refresh_token: OAuth refresh token

        Returns:
            New token information
        """
        pass

    @abstractmethod
    async def revoke_token(self, access_token: str) -> bool:
        """
        Revoke an access token.

        Args:
            access_token: Token to revoke

        Returns:
            True if successful
        """
        pass

    async def validate_token(self, access_token: str) -> bool:
        """
        Validate if a token is still valid.

        Args:
            access_token: Token to validate

        Returns:
            True if valid
        """
        try:
            user_info = await self.get_user_info(access_token)
            return user_info is not None
        except Exception:
            return False