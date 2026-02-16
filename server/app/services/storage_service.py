import logging
import os
from typing import Optional

import aiofiles

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Local filesystem storage service.

    Replaces the previous R2/S3 (boto3) implementation.  Files are stored
    under ``settings.storage_dir`` and served by FastAPI via the
    ``/api/files/{path}`` route defined in ``main.py``.
    """

    def __init__(self):
        self.base_dir = settings.storage_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _full_path(self, key: str) -> str:
        return os.path.join(self.base_dir, key)

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Write *data* to ``{storage_dir}/{key}``."""
        full_path = self._full_path(key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(data)
        logger.debug(f"Stored {len(data)} bytes at {full_path}")
        return key

    async def get_url(self, key: str) -> str:
        """Return the URL path served by FastAPI's static file route."""
        return f"/api/files/{key}"

    # Keep backward-compat alias
    async def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        return await self.get_url(key)

    async def delete(self, key: str) -> None:
        """Remove a file from disk."""
        full_path = self._full_path(key)
        try:
            os.remove(full_path)
        except FileNotFoundError:
            pass

    async def exists(self, key: str) -> bool:
        return os.path.isfile(self._full_path(key))
