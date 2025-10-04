"""
AWS S3 storage provider implementation.
"""

import boto3
from typing import BinaryIO, Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from app.services.storage.base import StorageProvider, StorageObject
from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Provider(StorageProvider):
    """AWS S3 storage provider."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})

        # Get configuration
        access_key = config.get("access_key") or settings.AWS_ACCESS_KEY_ID
        secret_key = config.get("secret_key") or settings.AWS_SECRET_ACCESS_KEY
        bucket_name = config.get("bucket") or settings.AWS_S3_BUCKET
        region = config.get("region") or settings.AWS_S3_REGION
        endpoint_url = config.get("endpoint_url") or settings.AWS_S3_ENDPOINT_URL

        # Initialize S3 client
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            endpoint_url=endpoint_url
        )
        self.bucket_name = bucket_name
        self.region = region

    async def upload_file(
        self,
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a file to S3.

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

            # Prepare extra args
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            if metadata:
                extra_args["Metadata"] = metadata

            # Upload file
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                key,
                ExtraArgs=extra_args
            )

            # Generate public URL
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
            logger.info(f"File uploaded to S3: {key}")
            return url

        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise

    async def download_file(self, key: str) -> bytes:
        """
        Download a file from S3.

        Args:
            key: Storage key

        Returns:
            File contents
        """
        try:
            key = self.sanitize_key(key)
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()

        except self.s3_client.exceptions.NoSuchKey:
            logger.error(f"File not found in S3: {key}")
            raise FileNotFoundError(f"File not found: {key}")
        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            raise

    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            key: Storage key

        Returns:
            True if successful
        """
        try:
            key = self.sanitize_key(key)
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"File deleted from S3: {key}")
            return True

        except Exception as e:
            logger.error(f"S3 delete failed: {e}")
            return False

    async def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            key: Storage key

        Returns:
            True if exists
        """
        try:
            key = self.sanitize_key(key)
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except self.s3_client.exceptions.ClientError:
            return False
        except Exception as e:
            logger.error(f"S3 existence check failed: {e}")
            return False

    async def get_file_info(self, key: str) -> Optional[StorageObject]:
        """
        Get file metadata from S3.

        Args:
            key: Storage key

        Returns:
            File metadata
        """
        try:
            key = self.sanitize_key(key)
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)

            return StorageObject(
                key=key,
                size=response["ContentLength"],
                content_type=response.get("ContentType"),
                etag=response.get("ETag", "").strip('"'),
                last_modified=response.get("LastModified"),
                metadata=response.get("Metadata", {})
            )

        except Exception as e:
            logger.error(f"S3 get file info failed: {e}")
            return None

    async def list_files(
        self,
        prefix: Optional[str] = None,
        max_keys: int = 1000
    ) -> List[StorageObject]:
        """
        List files in S3.

        Args:
            prefix: Key prefix filter
            max_keys: Maximum number of results

        Returns:
            List of storage objects
        """
        try:
            objects = []
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix or "",
                MaxKeys=max_keys
            )

            for obj in response.get("Contents", []):
                objects.append(
                    StorageObject(
                        key=obj["Key"],
                        size=obj["Size"],
                        etag=obj.get("ETag", "").strip('"'),
                        last_modified=obj.get("LastModified"),
                        metadata={}
                    )
                )

            return objects

        except Exception as e:
            logger.error(f"S3 list files failed: {e}")
            return []

    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        method: str = "GET"
    ) -> str:
        """
        Generate a presigned URL for S3.

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
                url = self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": key},
                    ExpiresIn=expiration
                )
            elif method.upper() == "PUT":
                url = self.s3_client.generate_presigned_url(
                    "put_object",
                    Params={"Bucket": self.bucket_name, "Key": key},
                    ExpiresIn=expiration
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            return url

        except Exception as e:
            logger.error(f"S3 presigned URL generation failed: {e}")
            raise

    async def copy_file(
        self,
        source_key: str,
        destination_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Copy a file within S3.

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

            copy_source = {"Bucket": self.bucket_name, "Key": source_key}

            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata
                extra_args["MetadataDirective"] = "REPLACE"

            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=destination_key,
                **extra_args
            )

            logger.info(f"File copied in S3: {source_key} -> {destination_key}")
            return True

        except Exception as e:
            logger.error(f"S3 copy failed: {e}")
            return False