import logging
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        if settings.storage_endpoint and settings.storage_access_key:
            self.client = boto3.client(
                "s3",
                endpoint_url=settings.storage_endpoint,
                aws_access_key_id=settings.storage_access_key,
                aws_secret_access_key=settings.storage_secret_key,
                config=BotoConfig(signature_version="s3v4"),
            )
            self.bucket = settings.storage_bucket
            self.enabled = True
        else:
            self.client = None
            self.bucket = None
            self.enabled = False
            logger.warning("Storage service not configured. File storage disabled.")

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        if not self.enabled:
            logger.warning(f"Storage disabled. Would upload to key: {key}")
            return key

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        if not self.enabled:
            return f"/api/storage/mock/{key}"

        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    async def delete(self, key: str) -> None:
        if not self.enabled:
            return

        self.client.delete_object(Bucket=self.bucket, Key=key)
