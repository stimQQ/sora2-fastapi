"""
Aliyun OSS storage provider implementation.
"""

import oss2
from typing import BinaryIO, Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from app.services.storage.base import StorageProvider, StorageObject
from app.core.config import settings

logger = logging.getLogger(__name__)


class OSSProvider(StorageProvider):
    """Aliyun OSS storage provider."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        super().__init__(config)

        # Get configuration
        access_key = config.get("access_key") or settings.ALIYUN_OSS_ACCESS_KEY
        secret_key = config.get("secret_key") or settings.ALIYUN_OSS_SECRET_KEY
        bucket_name = config.get("bucket") or settings.ALIYUN_OSS_BUCKET
        endpoint = config.get("endpoint") or settings.ALIYUN_OSS_ENDPOINT
        region = config.get("region") or settings.ALIYUN_OSS_REGION
        accelerate = config.get("accelerate", settings.ALIYUN_OSS_ACCELERATE)

        # Initialize OSS client
        if not endpoint:
            endpoint = f"oss-{region}.aliyuncs.com" if region else "oss-cn-hangzhou.aliyuncs.com"

        # Remove bucket name from endpoint if present (common mistake in config)
        if bucket_name and endpoint.startswith(f"{bucket_name}."):
            endpoint = endpoint[len(bucket_name) + 1:]

        # Use transfer acceleration endpoint if enabled
        if accelerate:
            # Transfer acceleration endpoint format: oss-accelerate.aliyuncs.com
            endpoint = "oss-accelerate.aliyuncs.com"
            logger.info(f"OSS transfer acceleration enabled: {endpoint}")

        # Ensure endpoint has https:// prefix
        if not endpoint.startswith('http'):
            endpoint = f"https://{endpoint}"

        auth = oss2.Auth(access_key, secret_key)
        self.bucket = oss2.Bucket(auth, endpoint, bucket_name)
        self.bucket_name = bucket_name
        self.endpoint = endpoint

    async def upload_file(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a file to OSS.

        Args:
            file: File-like object to upload
            key: Storage key
            content_type: MIME type
            metadata: Additional metadata

        Returns:
            Public URL
        """
        try:
            key = self.sanitize_key(key)

            # Prepare headers
            headers = {}
            if content_type:
                headers["Content-Type"] = content_type

            # Upload file without metadata in headers (to avoid signature issues)
            # Metadata will be passed as OSS user-defined metadata instead
            result = self.bucket.put_object(key, file, headers=headers if content_type else None)

            if result.status == 200:
                # Generate public URL using OSS SDK method
                # This ensures correct URL format regardless of endpoint configuration
                url = self.bucket.sign_url('GET', key, 3600 * 24 * 365 * 10)  # 10 year expiry for "permanent" link
                # Or use direct URL if bucket is public
                # url = f"https://{self.bucket_name}.{self.endpoint.replace('https://', '').replace('http://', '')}/{key}"
                logger.info(f"File uploaded to OSS: {key}")
                return url
            else:
                raise Exception(f"Upload failed with status {result.status}")

        except Exception as e:
            logger.error(f"OSS upload failed: {e}")
            raise

    async def download_file(self, key: str) -> bytes:
        """
        Download a file from OSS.

        Args:
            key: Storage key

        Returns:
            File contents
        """
        try:
            key = self.sanitize_key(key)
            result = self.bucket.get_object(key)
            return result.read()

        except oss2.exceptions.NoSuchKey:
            logger.error(f"File not found in OSS: {key}")
            raise FileNotFoundError(f"File not found: {key}")
        except Exception as e:
            logger.error(f"OSS download failed: {e}")
            raise

    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from OSS.

        Args:
            key: Storage key

        Returns:
            True if successful
        """
        try:
            key = self.sanitize_key(key)
            self.bucket.delete_object(key)
            logger.info(f"File deleted from OSS: {key}")
            return True

        except Exception as e:
            logger.error(f"OSS delete failed: {e}")
            return False

    async def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in OSS.

        Args:
            key: Storage key

        Returns:
            True if exists
        """
        try:
            key = self.sanitize_key(key)
            return self.bucket.object_exists(key)
        except Exception as e:
            logger.error(f"OSS existence check failed: {e}")
            return False

    async def get_file_info(self, key: str) -> Optional[StorageObject]:
        """
        Get file metadata from OSS.

        Args:
            key: Storage key

        Returns:
            File metadata
        """
        try:
            key = self.sanitize_key(key)

            if not self.bucket.object_exists(key):
                return None

            # Get object metadata
            result = self.bucket.head_object(key)

            # Extract metadata
            metadata = {}
            for header, value in result.headers.items():
                if header.startswith("x-oss-meta-"):
                    metadata[header[11:]] = value

            return StorageObject(
                key=key,
                size=int(result.headers.get("Content-Length", 0)),
                content_type=result.headers.get("Content-Type"),
                etag=result.headers.get("ETag", "").strip('"'),
                last_modified=datetime.strptime(
                    result.headers.get("Last-Modified"),
                    "%a, %d %b %Y %H:%M:%S %Z"
                ) if result.headers.get("Last-Modified") else None,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"OSS get file info failed: {e}")
            return None

    async def list_files(
        self,
        prefix: Optional[str] = None,
        max_keys: int = 1000
    ) -> List[StorageObject]:
        """
        List files in OSS.

        Args:
            prefix: Key prefix filter
            max_keys: Maximum number of results

        Returns:
            List of storage objects
        """
        try:
            objects = []

            # List objects with prefix
            for obj in oss2.ObjectIterator(
                self.bucket,
                prefix=prefix,
                max_keys=max_keys
            ):
                objects.append(
                    StorageObject(
                        key=obj.key,
                        size=obj.size,
                        content_type=obj.content_type,
                        etag=obj.etag.strip('"') if obj.etag else None,
                        last_modified=datetime.fromtimestamp(obj.last_modified),
                        metadata={}
                    )
                )

            return objects

        except Exception as e:
            logger.error(f"OSS list files failed: {e}")
            return []

    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET"
    ) -> str:
        """
        Generate a presigned URL for OSS.

        Args:
            key: Storage key
            expiration: Expiration in seconds
            method: HTTP method

        Returns:
            Presigned URL
        """
        try:
            key = self.sanitize_key(key)

            if method.upper() == "GET":
                url = self.bucket.sign_url("GET", key, expiration)
            elif method.upper() == "PUT":
                url = self.bucket.sign_url("PUT", key, expiration)
            else:
                raise ValueError(f"Unsupported method: {method}")

            return url

        except Exception as e:
            logger.error(f"OSS presigned URL generation failed: {e}")
            raise

    async def copy_file(
        self,
        source_key: str,
        destination_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Copy a file within OSS.

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

            # Prepare headers with metadata
            headers = {}
            if metadata:
                for k, v in metadata.items():
                    headers[f"x-oss-meta-{k}"] = v

            # Copy object
            self.bucket.copy_object(
                self.bucket_name,
                source_key,
                destination_key,
                headers=headers
            )

            logger.info(f"File copied in OSS: {source_key} -> {destination_key}")
            return True

        except Exception as e:
            logger.error(f"OSS copy failed: {e}")
            return False