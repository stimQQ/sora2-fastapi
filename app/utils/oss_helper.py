"""
OSS Helper Utilities
Provides convenient functions for uploading files to Aliyun OSS.
"""

import os
import uuid
import logging
from typing import Optional, BinaryIO
from pathlib import Path
from datetime import datetime
import mimetypes

from app.services.storage.factory import get_storage_provider
from app.core.config import settings

logger = logging.getLogger(__name__)


class OSSHelper:
    """Helper class for OSS operations."""

    def __init__(self):
        """Initialize OSS helper with storage provider."""
        self.storage = get_storage_provider()

    @staticmethod
    def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
        """
        Generate a unique filename with timestamp and UUID.

        Args:
            original_filename: Original filename
            prefix: Optional prefix (e.g., "images/", "videos/")

        Returns:
            Unique filename with path
        """
        # Extract extension
        ext = Path(original_filename).suffix

        # Generate unique name with date prefix for organization
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        unique_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now().strftime("%H%M%S")

        # Combine: prefix/YYYY/MM/DD/HHMMSS_uuid.ext
        filename = f"{prefix}{date_prefix}/{timestamp}_{unique_id}{ext}"

        return filename

    async def upload_image(
        self,
        file: BinaryIO,
        filename: str,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload an image file to OSS.

        Args:
            file: File binary data
            filename: Original filename
            metadata: Optional metadata

        Returns:
            Public URL of uploaded image

        Raises:
            ValueError: If file type is not allowed
        """
        # Validate file extension
        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(
                f"Invalid image format: {ext}. "
                f"Allowed: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"
            )

        # Generate unique key
        object_key = self.generate_unique_filename(filename, prefix="images/")

        # Detect content type
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type or not content_type.startswith("image/"):
            content_type = "image/jpeg"  # Default

        # Upload to OSS
        logger.info(f"Uploading image: {object_key}")
        url = await self.storage.upload_file(
            file=file,
            key=object_key,
            content_type=content_type,
            metadata=metadata
        )

        logger.info(f"Image uploaded successfully: {url}")
        return url

    async def upload_video(
        self,
        file: BinaryIO,
        filename: str,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a video file to OSS.

        Args:
            file: File binary data
            filename: Original filename
            metadata: Optional metadata

        Returns:
            Public URL of uploaded video

        Raises:
            ValueError: If file type is not allowed
        """
        # Validate file extension
        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
            raise ValueError(
                f"Invalid video format: {ext}. "
                f"Allowed: {', '.join(settings.ALLOWED_VIDEO_EXTENSIONS)}"
            )

        # Generate unique key
        object_key = self.generate_unique_filename(filename, prefix="videos/")

        # Detect content type
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type or not content_type.startswith("video/"):
            content_type = "video/mp4"  # Default

        # Upload to OSS
        logger.info(f"Uploading video: {object_key}")
        url = await self.storage.upload_file(
            file=file,
            key=object_key,
            content_type=content_type,
            metadata=metadata
        )

        logger.info(f"Video uploaded successfully: {url}")
        return url

    async def upload_file_from_path(
        self,
        file_path: str,
        prefix: str = "files/",
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file from local path to OSS.

        Args:
            file_path: Local file path
            prefix: Storage prefix (default: "files/")
            metadata: Optional metadata

        Returns:
            Public URL of uploaded file
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate unique key
        object_key = self.generate_unique_filename(path.name, prefix=prefix)

        # Detect content type
        content_type, _ = mimetypes.guess_type(str(path))

        # Upload to OSS
        with open(path, 'rb') as f:
            url = await self.storage.upload_file(
                file=f,
                key=object_key,
                content_type=content_type,
                metadata=metadata
            )

        logger.info(f"File uploaded from path: {file_path} -> {url}")
        return url

    async def get_upload_token(
        self,
        filename: str,
        file_type: str = "image",
        expires_in: int = 3600
    ) -> dict:
        """
        Generate upload token for client-side direct upload.

        Args:
            filename: Original filename
            file_type: File type ("image" or "video")
            expires_in: Token expiration in seconds

        Returns:
            Upload token dictionary with URL and credentials
        """
        # Validate file type
        ext = Path(filename).suffix.lower()

        if file_type == "image":
            if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
                raise ValueError(f"Invalid image extension: {ext}")
            prefix = "images/"
        elif file_type == "video":
            if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
                raise ValueError(f"Invalid video extension: {ext}")
            prefix = "videos/"
        else:
            raise ValueError(f"Invalid file type: {file_type}")

        # Generate unique key
        object_key = self.generate_unique_filename(filename, prefix=prefix)

        # Generate presigned URL for upload
        upload_url = await self.storage.generate_presigned_url(
            key=object_key,
            expiration=expires_in,
            method="PUT"
        )

        # Generate final public URL
        if hasattr(self.storage, 'get_public_url'):
            public_url = self.storage.get_public_url(object_key)
        else:
            # Fallback to constructing URL
            public_url = f"https://{settings.ALIYUN_OSS_BUCKET}.{settings.ALIYUN_OSS_ENDPOINT.replace('https://', '')}/{object_key}"

        return {
            "upload_url": upload_url,
            "public_url": public_url,
            "object_key": object_key,
            "expires_in": expires_in,
            "method": "PUT"
        }

    async def delete_file_by_url(self, url: str) -> bool:
        """
        Delete a file from OSS by its public URL.

        Args:
            url: Public URL of the file

        Returns:
            True if successful
        """
        try:
            # Extract object key from URL
            # URL format: https://bucket.endpoint/path/to/file.ext
            if settings.ALIYUN_OSS_BUCKET in url:
                # Split by bucket name and take the path part
                parts = url.split(f"{settings.ALIYUN_OSS_BUCKET}.{settings.ALIYUN_OSS_ENDPOINT.replace('https://', '')}/")
                if len(parts) == 2:
                    object_key = parts[1]
                    return await self.storage.delete_file(object_key)

            logger.warning(f"Could not extract object key from URL: {url}")
            return False

        except Exception as e:
            logger.error(f"Failed to delete file by URL: {e}")
            return False


# Convenience functions
oss_helper = OSSHelper()


async def upload_image(file: BinaryIO, filename: str, metadata: Optional[dict] = None) -> str:
    """Upload an image file to OSS."""
    return await oss_helper.upload_image(file, filename, metadata)


async def upload_video(file: BinaryIO, filename: str, metadata: Optional[dict] = None) -> str:
    """Upload a video file to OSS."""
    return await oss_helper.upload_video(file, filename, metadata)


async def get_upload_token(filename: str, file_type: str = "image", expires_in: int = 3600) -> dict:
    """Generate upload token for client-side direct upload."""
    return await oss_helper.get_upload_token(filename, file_type, expires_in)
