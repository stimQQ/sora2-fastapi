"""
WeChat OAuth authentication provider.
"""

import httpx
import json
from typing import Dict, Any, Optional
from urllib.parse import urlencode
import logging

from app.services.auth.base import AuthProvider, AuthUserInfo
from app.core.config import settings

logger = logging.getLogger(__name__)


class WeChatProvider(AuthProvider):
    """WeChat OAuth2.0 authentication provider."""

    BASE_URL = "https://api.weixin.qq.com"
    OAUTH_BASE_URL = "https://open.weixin.qq.com"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})
        self.app_id = config.get("app_id") or settings.WECHAT_APP_ID
        self.app_secret = config.get("app_secret") or settings.WECHAT_APP_SECRET

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """
        Get WeChat OAuth authorization URL.

        Args:
            state: State parameter for CSRF protection
            redirect_uri: Callback URL

        Returns:
            WeChat authorization URL
        """
        params = {
            "appid": self.app_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "snsapi_userinfo",
            "state": state,
        }

        # Different URLs for WeChat browser vs H5
        if self.config.get("is_wechat_browser", False):
            base_url = f"{self.OAUTH_BASE_URL}/connect/oauth2/authorize"
        else:
            base_url = f"{self.OAUTH_BASE_URL}/connect/qrconnect"

        return f"{base_url}?{urlencode(params)}#wechat_redirect"

    async def exchange_code_for_token(self, code: str, redirect_uri: str = None) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from WeChat
            redirect_uri: Not used in WeChat OAuth

        Returns:
            Token information including access_token and openid
        """
        url = f"{self.BASE_URL}/sns/oauth2/access_token"
        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "code": code,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()

            if "errcode" in data and data["errcode"] != 0:
                logger.error(f"WeChat token exchange failed: {data}")
                raise Exception(f"WeChat OAuth error: {data.get('errmsg', 'Unknown error')}")

            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "openid": data["openid"],
                "unionid": data.get("unionid"),
                "scope": data.get("scope"),
                "expires_in": data.get("expires_in", 7200),
            }

    async def get_user_info(self, access_token: str, openid: str = None) -> AuthUserInfo:
        """
        Get user information from WeChat.

        Args:
            access_token: WeChat access token
            openid: WeChat OpenID (required for WeChat)

        Returns:
            Standardized user information
        """
        if not openid:
            # If openid is not provided, it should be stored with the access_token
            raise ValueError("OpenID is required for WeChat user info")

        url = f"{self.BASE_URL}/sns/userinfo"
        params = {
            "access_token": access_token,
            "openid": openid,
            "lang": "zh_CN",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()

            if "errcode" in data and data["errcode"] != 0:
                logger.error(f"WeChat get user info failed: {data}")
                raise Exception(f"WeChat API error: {data.get('errmsg', 'Unknown error')}")

            return AuthUserInfo(
                provider="wechat",
                provider_user_id=data["openid"],
                nickname=data.get("nickname"),
                avatar=data.get("headimgurl"),
                raw_data=data,
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh WeChat access token.

        Args:
            refresh_token: WeChat refresh token

        Returns:
            New token information
        """
        url = f"{self.BASE_URL}/sns/oauth2/refresh_token"
        params = {
            "appid": self.app_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()

            if "errcode" in data and data["errcode"] != 0:
                logger.error(f"WeChat token refresh failed: {data}")
                raise Exception(f"WeChat refresh error: {data.get('errmsg', 'Unknown error')}")

            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "openid": data["openid"],
                "scope": data.get("scope"),
                "expires_in": data.get("expires_in", 7200),
            }

    async def revoke_token(self, access_token: str) -> bool:
        """
        WeChat doesn't provide a revoke endpoint.
        Tokens expire automatically after 2 hours.

        Args:
            access_token: Token to revoke

        Returns:
            Always returns True
        """
        logger.info("WeChat tokens expire automatically and cannot be revoked manually")
        return True

    async def validate_token(self, access_token: str, openid: str = None) -> bool:
        """
        Validate if a WeChat token is still valid.

        Args:
            access_token: Token to validate
            openid: WeChat OpenID

        Returns:
            True if valid
        """
        if not openid:
            return False

        url = f"{self.BASE_URL}/sns/auth"
        params = {
            "access_token": access_token,
            "openid": openid,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                data = response.json()
                return data.get("errcode", -1) == 0
        except Exception as e:
            logger.error(f"WeChat token validation failed: {e}")
            return False