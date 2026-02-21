from typing import Protocol
from uuid import UUID

from src.backend_fastapi.database.models import File, Image


class IMediaRepository(Protocol):
    """
    Interface for Media Repository (Protocol).
    Handles operations for both physical Files (CAS) and user Images.
    """

    # --- File Operations (CAS) ---
    async def get_file_by_hash(self, file_hash: str) -> File | None:
        """
        Check if a file with this hash already exists (Deduplication).
        """
        ...

    async def create_file(self, file_hash: str, size_bytes: int, mime_type: str, path: str) -> File:
        """
        Register a new physical file in the database.
        """
        ...

    async def delete_file(self, file_hash: str) -> None:
        """
        Delete physical file record (used by GC).
        """
        ...

    async def get_usage_count(self, file_hash: str) -> int:
        """
        Count how many images reference this file hash.
        """
        ...

    # --- Image Operations (User Assets) ---
    async def create_image(self, user_id: UUID, file_hash: str, filename: str) -> Image:
        """
        Link a user to a file (create an asset).
        """
        ...

    async def get_image_by_id(self, image_id: UUID) -> Image | None:
        """
        Get image metadata by ID.
        """
        ...

    async def get_public_images(self, limit: int, offset: int) -> list[Image]:
        """
        Get gallery for public feed.
        """
        ...

    async def get_images_by_user(self, user_id: UUID, limit: int, offset: int) -> list[Image]:
        """
        Get gallery for a specific user.
        """
        ...

    async def delete_image(self, image_id: UUID) -> None:
        """
        Delete user image (asset).
        """
        ...

    async def commit(self) -> None:
        """
        Commit the current transaction.
        """
        ...
