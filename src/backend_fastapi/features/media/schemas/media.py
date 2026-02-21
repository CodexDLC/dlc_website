from datetime import datetime
from uuid import UUID

from pydantic import computed_field

from src.backend_fastapi.core.config import settings
from src.backend_fastapi.core.schemas.base import BaseResponse


class FileRead(BaseResponse):
    """
    Schema for reading File metadata (CAS).
    """

    hash: str
    size_bytes: int
    mime_type: str
    created_at: datetime


class ImageRead(BaseResponse):
    """
    Schema for reading Image metadata (User Asset).
    """

    id: UUID
    filename: str
    created_at: datetime
    file: FileRead

    @computed_field
    def url(self) -> str:
        """
        Direct absolute URL to the original image served by Nginx.
        Format: {SITE_URL}/media/storage/ab/cd/hash.ext
        """
        h = self.file.hash

        # Map mime_type to extension for URL generation
        # This must match ALLOWED_MIME_TYPES in MediaService
        mime_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        ext = mime_map.get(self.file.mime_type, "")

        # Sharding logic: first 2 chars, next 2 chars
        return f"{settings.SITE_URL}/media/storage/{h[:2]}/{h[2:4]}/{h}{ext}"

    @computed_field
    def src(self) -> str:
        """
        Direct absolute URL to the thumbnail served by Nginx.
        Format: {SITE_URL}/media/storage/ab/cd/hash_thumb.jpg
        """
        h = self.file.hash
        return f"{settings.SITE_URL}/media/storage/{h[:2]}/{h[2:4]}/{h}_thumb.jpg"
