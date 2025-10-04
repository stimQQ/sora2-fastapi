"""
Base storage provider interface.
All storage providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional, Dict, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel
from pathlib import Path


class StorageObject(BaseModel):
    """Storage object metadata."""
    key: str
    size: int
    content_type: Optional[str] = None
    etag: Optional[str] = None
    last_modified: Optional[datetime] = None
    metadata: Dict[str, str] = {}


class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the storage provider with configuration.

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.provider_name = self.__class__.__name__.lower().replace('provider', '')

    @abstractmethod
    async def upload_file(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a file to storage.

        Args:
            file: File-like object to upload
            key: Storage key (path)
            content_type: MIME type of the file
            metadata: Additional metadata

        Returns:
            Public URL or storage path
        """
        pass

    @abstractmethod
    async def download_file(self, key: str) -> bytes:
        """
        Download a file from storage.

        Args:
            key: Storage key

        Returns:
            File contents as bytes
        """
        pass

    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from storage.

        Args:
            key: Storage key

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def file_exists(self, key: str) -> bool:
        """
        Check if a file exists.

        Args:
            key: Storage key

        Returns:
            True if file exists
        """
        pass

    @abstractmethod
    async def get_file_info(self, key: str) -> Optional[StorageObject]:
        """
        Get file metadata.

        Args:
            key: Storage key

        Returns:
            File metadata or None if not found
        """
        pass

    @abstractmethod
    async def list_files(
        self,
        prefix: Optional[str] = None,
        max_keys: int = 1000
    ) -> List[StorageObject]:
        """
        List files in storage.

        Args:
            prefix: Filter by key prefix
            max_keys: Maximum number of keys to return

        Returns:
            List of storage objects
        """
        pass

    @abstractmethod
    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET"
    ) -> str:
        """
        Generate a presigned URL for direct access.

        Args:
            key: Storage key
            expiration: URL expiration time in seconds
            method: HTTP method (GET or PUT)

        Returns:
            Presigned URL
        """
        pass

    @abstractmethod
    async def copy_file(
        self,
        source_key: str,
        destination_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Copy a file within storage.

        Args:
            source_key: Source storage key
            destination_key: Destination storage key
            metadata: New metadata for the copy

        Returns:
            True if successful
        """
        pass

    async def move_file(
        self,
        source_key: str,
        destination_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Move a file within storage.

        Args:
            source_key: Source storage key
            destination_key: Destination storage key
            metadata: New metadata for the moved file

        Returns:
            True if successful
        """
        # Default implementation: copy then delete
        success = await self.copy_file(source_key, destination_key, metadata)
        if success:
            await self.delete_file(source_key)
        return success

    def sanitize_key(self, key: str) -> str:
        """
        Sanitize a storage key to ensure it's valid.

        Args:
            key: Original key

        Returns:
            Sanitized key
        """
        # Remove leading slashes
        key = key.lstrip("/")

        # Replace spaces and special characters
        key = key.replace(" ", "_")
        key = key.replace("#", "_")
        key = key.replace("?", "_")

        return key

    def generate_unique_key(
        self,
        filename: str,
        prefix: Optional[str] = None,
        timestamp: bool = True
    ) -> str:
        """
        Generate a unique storage key.

        Args:
            filename: Original filename
            prefix: Optional prefix for the key
            timestamp: Whether to include timestamp

        Returns:
            Unique storage key
        """
        from uuid import uuid4

        # Extract extension
        path = Path(filename)
        extension = path.suffix

        # Build key components
        components = []

        if prefix:
            components.append(prefix.rstrip("/"))

        if timestamp:
            components.append(datetime.utcnow().strftime("%Y/%m/%d"))

        # Add UUID for uniqueness
        unique_id = str(uuid4())[:8]
        name = f"{path.stem}_{unique_id}{extension}"
        components.append(name)

        # Join and sanitize
        key = "/".join(components)
        return self.sanitize_key(key)