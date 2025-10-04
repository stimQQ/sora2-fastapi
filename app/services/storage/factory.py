"""
Storage factory for creating storage provider instances.
"""

from typing import Optional, Dict, Any
import logging

from app.services.storage.base import StorageProvider
from app.services.storage.providers.oss import OSSProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageFactory:
    """Factory for creating storage provider instances."""

    _instances: Dict[str, StorageProvider] = {}

    @classmethod
    def get_provider(
        cls,
        backend: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> StorageProvider:
        """
        Get a storage provider instance.

        Args:
            backend: Storage backend type (oss, s3, local).
                    If None, uses settings.STORAGE_BACKEND
            config: Optional configuration override

        Returns:
            Storage provider instance

        Raises:
            ValueError: If backend is not supported
        """
        backend = backend or settings.STORAGE_BACKEND

        # Return cached instance if exists
        if backend in cls._instances and not config:
            return cls._instances[backend]

        # Create new provider instance
        provider = cls._create_provider(backend, config)

        # Cache the instance
        if not config:
            cls._instances[backend] = provider

        return provider

    @classmethod
    def _create_provider(
        cls,
        backend: str,
        config: Optional[Dict[str, Any]] = None
    ) -> StorageProvider:
        """
        Create a storage provider instance.

        Args:
            backend: Storage backend type
            config: Provider configuration

        Returns:
            Storage provider instance

        Raises:
            ValueError: If backend is not supported
        """
        if backend == "oss":
            return OSSProvider(config)
        elif backend == "s3":
            # Import here to avoid circular dependency
            from app.services.storage.providers.s3 import S3Provider
            return S3Provider(config)
        elif backend == "local":
            # Import here to avoid circular dependency
            from app.services.storage.providers.local import LocalProvider
            return LocalProvider(config)
        else:
            raise ValueError(f"Unsupported storage backend: {backend}")

    @classmethod
    def clear_cache(cls):
        """Clear the provider cache."""
        cls._instances.clear()
        logger.info("Storage provider cache cleared")


# Convenience function for getting default provider
def get_storage_provider() -> StorageProvider:
    """
    Get the default storage provider based on settings.

    Returns:
        Storage provider instance
    """
    return StorageFactory.get_provider()