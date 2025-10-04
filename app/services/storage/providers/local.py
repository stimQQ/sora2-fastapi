"""
Local filesystem storage provider implementation.
"""

import aiofiles
import aiofiles.os
from pathlib import Path
from typing import BinaryIO, Optional, Dict, Any, List
from datetime import datetime
import logging
import shutil

from app.services.storage.base import StorageProvider, StorageObject
from app.core.config import settings

logger = logging.getLogger(__name__)


class LocalProvider(StorageProvider):
    """Local filesystem storage provider."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})

        # Get storage path from config or settings
        self.storage_path = Path(config.get("storage_path", settings.LOCAL_STORAGE_PATH))

        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized at: {self.storage_path}")

    def _get_full_path(self, key: str) -> Path:
        """Get full filesystem path for a key."""
        key = self.sanitize_key(key)
        return self.storage_path / key

    def _get_metadata_path(self, key: str) -> Path:
        """Get path for metadata file."""
        return self._get_full_path(key).with_suffix(self._get_full_path(key).suffix + ".meta")

    async def upload_file(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a file to local storage.

        Args:
            file: File-like object to upload
            key: Storage key
            content_type: MIME type
            metadata: Additional metadata

        Returns:
            File path URL
        """
        try:
            key = self.sanitize_key(key)
            file_path = self._get_full_path(key)

            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            async with aiofiles.open(file_path, "wb") as f:
                content = file.read()
                await f.write(content)

            # Save metadata if provided
            if metadata or content_type:
                meta_path = self._get_metadata_path(key)
                meta_data = metadata or {}
                if content_type:
                    meta_data["content_type"] = content_type
                meta_data["uploaded_at"] = datetime.utcnow().isoformat()

                async with aiofiles.open(meta_path, "w") as f:
                    import json
                    await f.write(json.dumps(meta_data))

            # Return file URL (relative path)
            file_url = f"/storage/{key}"
            logger.info(f"File uploaded to local storage: {key}")
            return file_url

        except Exception as e:
            logger.error(f"Local storage upload failed: {e}")
            raise

    async def download_file(self, key: str) -> bytes:
        """
        Download a file from local storage.

        Args:
            key: Storage key

        Returns:
            File contents
        """
        try:
            key = self.sanitize_key(key)
            file_path = self._get_full_path(key)

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {key}")

            async with aiofiles.open(file_path, "rb") as f:
                return await f.read()

        except FileNotFoundError:
            logger.error(f"File not found in local storage: {key}")
            raise
        except Exception as e:
            logger.error(f"Local storage download failed: {e}")
            raise

    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from local storage.

        Args:
            key: Storage key

        Returns:
            True if successful
        """
        try:
            key = self.sanitize_key(key)
            file_path = self._get_full_path(key)
            meta_path = self._get_metadata_path(key)

            # Delete file
            if file_path.exists():
                await aiofiles.os.remove(file_path)

            # Delete metadata
            if meta_path.exists():
                await aiofiles.os.remove(meta_path)

            logger.info(f"File deleted from local storage: {key}")
            return True

        except Exception as e:
            logger.error(f"Local storage delete failed: {e}")
            return False

    async def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in local storage.

        Args:
            key: Storage key

        Returns:
            True if exists
        """
        try:
            key = self.sanitize_key(key)
            file_path = self._get_full_path(key)
            return file_path.exists()
        except Exception as e:
            logger.error(f"Local storage existence check failed: {e}")
            return False

    async def get_file_info(self, key: str) -> Optional[StorageObject]:
        """
        Get file metadata from local storage.

        Args:
            key: Storage key

        Returns:
            File metadata
        """
        try:
            key = self.sanitize_key(key)
            file_path = self._get_full_path(key)

            if not file_path.exists():
                return None

            # Get file stats
            stats = file_path.stat()

            # Load metadata if exists
            metadata = {}
            content_type = None
            meta_path = self._get_metadata_path(key)
            if meta_path.exists():
                async with aiofiles.open(meta_path, "r") as f:
                    import json
                    meta_data = json.loads(await f.read())
                    content_type = meta_data.pop("content_type", None)
                    metadata = meta_data

            return StorageObject(
                key=key,
                size=stats.st_size,
                content_type=content_type,
                last_modified=datetime.fromtimestamp(stats.st_mtime),
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Local storage get file info failed: {e}")
            return None

    async def list_files(
        self,
        prefix: Optional[str] = None,
        max_keys: int = 1000
    ) -> List[StorageObject]:
        """
        List files in local storage.

        Args:
            prefix: Key prefix filter
            max_keys: Maximum number of results

        Returns:
            List of storage objects
        """
        try:
            objects = []
            search_path = self.storage_path

            if prefix:
                search_path = self.storage_path / prefix

            if not search_path.exists():
                return []

            # Recursively find all files
            for file_path in search_path.rglob("*"):
                if file_path.is_file() and not file_path.suffix == ".meta":
                    # Get relative key
                    key = str(file_path.relative_to(self.storage_path))

                    # Get file info
                    file_info = await self.get_file_info(key)
                    if file_info:
                        objects.append(file_info)

                    # Check max keys
                    if len(objects) >= max_keys:
                        break

            return objects

        except Exception as e:
            logger.error(f"Local storage list files failed: {e}")
            return []

    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET"
    ) -> str:
        """
        Generate a presigned URL for local storage.

        Note: Local storage doesn't support true presigned URLs,
        so this returns a regular file URL.

        Args:
            key: Storage key
            expiration: Expiration in seconds (ignored)
            method: HTTP method (ignored)

        Returns:
            File URL
        """
        key = self.sanitize_key(key)
        return f"/storage/{key}"

    async def copy_file(
        self,
        source_key: str,
        destination_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Copy a file within local storage.

        Args:
            source_key: Source key
            destination_key: Destination key
            metadata: New metadata

        Returns:
            True if successful
        """
        try:
            source_key = self.sanitize_key(source_key)
            destination_key = self.sanitize_key(destination_key)

            source_path = self._get_full_path(source_key)
            destination_path = self._get_full_path(destination_key)

            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_key}")

            # Create destination directory
            destination_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source_path, destination_path)

            # Update metadata if provided
            if metadata:
                meta_path = self._get_metadata_path(destination_key)
                async with aiofiles.open(meta_path, "w") as f:
                    import json
                    metadata["copied_at"] = datetime.utcnow().isoformat()
                    await f.write(json.dumps(metadata))

            logger.info(f"File copied in local storage: {source_key} -> {destination_key}")
            return True

        except Exception as e:
            logger.error(f"Local storage copy failed: {e}")
            return False