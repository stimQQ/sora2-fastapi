"""
Core configuration module for the application.
Handles all environment variables and configuration settings.
"""

from typing import List, Optional, Dict, Any
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
import os
from pathlib import Path

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Settings
    APP_NAME: str = "Video Animation Platform"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="production", pattern="^(development|staging|production)$")

    # Server Settings
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    WORKERS: int = Field(default=4)

    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    CORS_ALLOWED_ORIGINS: str = ""  # Will be parsed to List[str] by validator
    PROXY_API_KEY: str = Field(...)

    # DashScope API
    QWEN_VIDEO_API_KEY: str = Field(...)
    DASHSCOPE_API_URL: str = "https://dashscope.aliyuncs.com/api/v1"
    DASHSCOPE_TIMEOUT: int = 30

    # Sora 2 API
    SORA_API_KEY: str = Field(...)
    SORA_API_URL: str = "https://api.kie.ai/api/v1"
    SORA_TIMEOUT: int = 30
    SORA_CALLBACK_URL: Optional[str] = None

    # Database Configuration
    DATABASE_URL_MASTER: str = Field(...)
    DATABASE_URL_SLAVES: str = ""  # Comma-separated, will be parsed by validator
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False

    # Redis Configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = None
    REDIS_POOL_SIZE: int = 10
    REDIS_DECODE_RESPONSES: bool = True
    CACHE_TTL: int = 3600  # 1 hour default

    # Celery Configuration
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = "Asia/Shanghai"

    # Storage Configuration
    STORAGE_BACKEND: str = Field(default="oss", pattern="^(oss|s3|local)$")

    # Aliyun OSS
    ALIYUN_OSS_ACCESS_KEY: Optional[str] = None
    ALIYUN_OSS_SECRET_KEY: Optional[str] = None
    ALIYUN_OSS_BUCKET: Optional[str] = None
    ALIYUN_OSS_ENDPOINT: Optional[str] = None
    ALIYUN_OSS_REGION: str = "cn-beijing"

    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_S3_REGION: str = "ap-southeast-1"
    AWS_S3_ENDPOINT_URL: Optional[str] = None

    # Local Storage
    LOCAL_STORAGE_PATH: Path = BASE_DIR / "uploads"

    # SMS Configuration (Aliyun)
    ALIYUN_SMS_ACCESS_KEY: Optional[str] = None
    ALIYUN_SMS_SECRET_KEY: Optional[str] = None
    ALIYUN_SMS_SIGN_NAME: Optional[str] = None
    ALIYUN_SMS_TEMPLATE_CODE: Optional[str] = None

    # Authentication Providers
    AUTH_PROVIDERS_ENABLED: str = "wechat,google"  # Comma-separated

    # WeChat OAuth
    WECHAT_APP_ID: Optional[str] = None
    WECHAT_APP_SECRET: Optional[str] = None
    WECHAT_REDIRECT_URI: Optional[str] = None

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

    # Payment Providers
    PAYMENT_PROVIDERS_ENABLED: str = "wechat_pay,stripe"  # Comma-separated

    # WeChat Pay
    WECHAT_PAY_APP_ID: Optional[str] = None
    WECHAT_PAY_MERCHANT_ID: Optional[str] = None
    WECHAT_PAY_API_KEY: Optional[str] = None
    WECHAT_PAY_CERT_PATH: Optional[Path] = None
    WECHAT_PAY_NOTIFY_URL: Optional[str] = None

    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_WEBHOOK_URL: Optional[str] = None

    # Region Detection
    GEOIP_DATABASE_PATH: Path = BASE_DIR / "data" / "GeoLite2-City.mmdb"
    DEFAULT_REGION: str = "CN"
    SUPPORTED_REGIONS: str = "CN,US,EU,ASIA"  # Comma-separated

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_STORAGE_URL: Optional[str] = None  # Uses Redis URL if not specified

    # File Upload
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_IMAGE_EXTENSIONS: List[str] = Field(default_factory=lambda: [".jpg", ".jpeg", ".png", ".webp"])
    ALLOWED_VIDEO_EXTENSIONS: List[str] = Field(default_factory=lambda: [".mp4", ".mov", ".avi", ".webm"])

    # Task Processing
    TASK_TIMEOUT: int = 600  # 10 minutes
    TASK_MAX_RETRIES: int = 3
    TASK_RETRY_DELAY: int = 60  # 1 minute
    TASK_RESULT_EXPIRY: int = 86400  # 24 hours

    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    SENTRY_DSN: Optional[str] = None

    # Logging
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FORMAT: str = "json"
    LOG_FILE_PATH: Optional[Path] = BASE_DIR / "logs" / "app.log"
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"

    # Email (for notifications)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None

    # Credits System - Updated 2025-09-30
    DEFAULT_USER_CREDITS: int = 100  # New user initial credits (was 10)

    # Video generation pricing (per second)
    CREDITS_PER_SECOND_STANDARD: int = 10  # Standard version (wan-std)
    CREDITS_PER_SECOND_PRO: int = 14  # Pro version (wan-pro)

    # Sora 2 pricing (per video, fixed cost)
    CREDITS_SORA_TEXT_TO_VIDEO_STANDARD: int = 20  # Text-to-video standard quality
    CREDITS_SORA_TEXT_TO_VIDEO_HD: int = 30  # Text-to-video HD quality
    CREDITS_SORA_IMAGE_TO_VIDEO_STANDARD: int = 25  # Image-to-video standard quality
    CREDITS_SORA_IMAGE_TO_VIDEO_HD: int = 35  # Image-to-video HD quality

    # Credit value
    CREDIT_VALUE_RMB: float = 0.1  # 1 credit = ¥0.1 RMB

    # Credit packages (name, credits, price in RMB, unit_price)
    CREDIT_PACKAGES: Dict[str, Dict[str, Any]] = {
        "trial": {
            "name": "体验包",
            "credits": 500,
            "price": 50.0,
            "unit_price": 0.10
        },
        "standard": {
            "name": "标准包",
            "credits": 1100,
            "bonus": 0,
            "price": 100.0,
            "unit_price": 0.091
        },
        "value": {
            "name": "超值包",
            "credits": 6000,
            "bonus": 0,
            "price": 500.0,
            "unit_price": 0.083
        },
        "premium": {
            "name": "豪华包",
            "credits": 13000,
            "bonus": 0,
            "price": 1000.0,
            "unit_price": 0.076
        }
    }

    # Task rewards
    CREDITS_INVITE_REWARD: int = 100  # Invite new user (was 5)
    CREDITS_DAILY_SIGNIN: int = 10  # Daily sign-in (was 1)
    CREDITS_SHARE_VIDEO: int = 10  # Share video (was 1)
    CREDITS_SHARE_VIDEO_MAX_DAILY: int = 5  # Max shares per day

    # Credit expiry
    CREDIT_EXPIRY_MONTHS: int = 6  # Credits expire after 6 months

    # Legacy fields (deprecated - kept for backward compatibility)
    CREDITS_PER_ANIMATE_MOVE: int = 2  # Deprecated: Use CREDITS_PER_SECOND_STANDARD instead
    CREDITS_PER_ANIMATE_MIX: int = 3  # Deprecated: Use CREDITS_PER_SECOND_STANDARD instead

    @validator("CORS_ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if v is None or v == "":
            return ""
        return v

    @validator("DATABASE_URL_SLAVES", pre=True)
    def parse_slave_urls(cls, v):
        if v is None or v == "":
            return ""
        return v

    @validator("LOCAL_STORAGE_PATH")
    def create_storage_path(cls, v):
        v.mkdir(parents=True, exist_ok=True)
        return v

    @validator("LOG_FILE_PATH")
    def create_log_path(cls, v):
        if v:
            try:
                v.parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                # Skip if we can't create the directory (e.g., in Docker mount or read-only filesystem)
                pass
        return v

    @property
    def cors_origins(self) -> List[str]:
        """Get CORS allowed origins as a list."""
        if not self.CORS_ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def auth_providers(self) -> List[str]:
        """Get enabled auth providers as a list."""
        if not self.AUTH_PROVIDERS_ENABLED:
            return []
        return [p.strip() for p in self.AUTH_PROVIDERS_ENABLED.split(",") if p.strip()]

    @property
    def payment_providers(self) -> List[str]:
        """Get enabled payment providers as a list."""
        if not self.PAYMENT_PROVIDERS_ENABLED:
            return []
        return [p.strip() for p in self.PAYMENT_PROVIDERS_ENABLED.split(",") if p.strip()]

    @property
    def supported_regions_list(self) -> List[str]:
        """Get supported regions as a list."""
        if not self.SUPPORTED_REGIONS:
            return []
        return [r.strip() for r in self.SUPPORTED_REGIONS.split(",") if r.strip()]

    @property
    def slave_database_urls(self) -> List[str]:
        """Get slave database URLs as a list."""
        if not self.DATABASE_URL_SLAVES:
            return []
        return [url.strip() for url in self.DATABASE_URL_SLAVES.split(",") if url.strip()]

    @property
    def database_urls(self) -> Dict[str, Any]:
        """Get all database URLs with read/write designation."""
        slaves = self.slave_database_urls or [self.DATABASE_URL_MASTER]
        return {
            "master": self.DATABASE_URL_MASTER,
            "slaves": slaves
        }

    @property
    def redis_dsn(self) -> str:
        """Get Redis DSN with password if configured."""
        if self.REDIS_PASSWORD:
            return self.REDIS_URL.replace("redis://", f"redis://:{self.REDIS_PASSWORD}@")
        return self.REDIS_URL

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
        # Disable JSON parsing for env variables
        env_parse_enums=None,
        env_ignore_empty=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Use this function to get settings throughout the application.
    """
    return Settings()


# Create a global settings instance
settings = get_settings()