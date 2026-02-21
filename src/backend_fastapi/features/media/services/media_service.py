import hashlib
import os
import shutil
import uuid
from pathlib import Path
from uuid import UUID

import aiofiles  # type: ignore
import magic
from aiofiles import os as aios  # type: ignore
from fastapi import UploadFile
from loguru import logger
from PIL import Image as PILImage
from starlette.concurrency import run_in_threadpool

from src.backend_fastapi.core.config import settings
from src.backend_fastapi.core.exceptions import (
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from src.backend_fastapi.features.media.contracts.media_repository import IMediaRepository
from src.backend_fastapi.features.media.schemas.media import ImageRead


class MediaService:
    """
    Business logic for Media Domain.
    Handles file validation, CAS storage, deduplication, and image management.
    """

    ALLOWED_MIME_TYPES = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }

    def __init__(self, repository: IMediaRepository):
        self.repository = repository
        self.chunk_size = 64 * 1024  # 64KB
        self.max_upload_size = settings.MAX_UPLOAD_SIZE

        self.temp_dir = settings.UPLOAD_DIR / "temp"
        self.storage_dir = settings.UPLOAD_DIR / "storage"

        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def upload_image(self, user_id: UUID, file: UploadFile) -> ImageRead:
        """
        Main entry point for image upload.

        Returns:
            ImageRead: Uploaded image metadata.
        """
        logger.info(f"MediaService | action=upload_start user_id={user_id} filename={file.filename}")

        temp_filename = f"upload_{uuid.uuid4()}.tmp"
        temp_path = self.temp_dir / temp_filename

        try:
            # Stream to temp + Hash calculation
            file_hash, size_bytes = await self._process_stream_to_temp(file, temp_path)
            logger.debug(f"MediaService | action=file_processed hash={file_hash} size={size_bytes}")

            # Magic Bytes validation
            mime_type = await self._validate_file_type(temp_path)
            logger.debug(f"MediaService | action=magic_bytes_ok mime={mime_type}")

            # Deduplication check
            existing_file = await self.repository.get_file_by_hash(file_hash)

            if existing_file:
                logger.info(f"MediaService | action=deduplication_hit hash={file_hash}")
                await self._remove_file(temp_path)

                image = await self.repository.create_image(
                    user_id=user_id,
                    file_hash=file_hash,
                    filename=file.filename or "unknown",
                )
                await self.repository.commit()
                return ImageRead.model_validate(image)

            else:
                logger.info(f"MediaService | action=deduplication_miss hash={file_hash}")

                # Determine extension
                ext = self.ALLOWED_MIME_TYPES.get(mime_type, "")
                target_path = self._get_storage_path(file_hash, ext)

                # Atomic Move: temp -> storage
                await run_in_threadpool(shutil.move, str(temp_path), str(target_path))

                try:
                    await self._generate_thumbnail(target_path, file_hash)
                except Exception as e:
                    logger.error(f"MediaService | action=thumbnail_failed hash={file_hash} error={e}", exc_info=True)

                # DB Registration
                await self.repository.create_file(
                    file_hash=file_hash,
                    size_bytes=size_bytes,
                    mime_type=mime_type,
                    path=str(target_path),
                )

                image = await self.repository.create_image(
                    user_id=user_id,
                    file_hash=file_hash,
                    filename=file.filename or "unknown",
                )
                await self.repository.commit()
                return ImageRead.model_validate(image)

        except Exception as e:
            logger.error(f"MediaService | action=upload_failed error={e}", exc_info=True)
            if temp_path.exists():
                await self._remove_file(temp_path)
            raise e

    async def get_feed(self, limit: int = 20, offset: int = 0) -> list[ImageRead]:
        """
        Get public feed of images.

        Returns:
            list[ImageRead]: List of public images.
        """
        images = await self.repository.get_public_images(limit=limit, offset=offset)
        return [ImageRead.model_validate(img) for img in images]

    async def get_user_gallery(self, user_id: UUID, limit: int = 20, offset: int = 0) -> list[ImageRead]:
        """
        Get images for a specific user.

        Returns:
            list[ImageRead]: List of user's images.
        """
        images = await self.repository.get_images_by_user(user_id=user_id, limit=limit, offset=offset)
        return [ImageRead.model_validate(img) for img in images]

    async def delete_image(self, user_id: UUID, image_id: UUID) -> None:
        """
        Delete an image.
        Checks ownership before deletion.
        Implements Garbage Collection (GC) for physical files.
        """
        image = await self.repository.get_image_by_id(image_id)
        if not image:
            logger.warning(f"MediaService | action=delete_failed reason=not_found image_id={image_id}")
            raise NotFoundException(detail="Image not found")

        if image.user_id != user_id:
            logger.warning(
                f"MediaService | action=delete_failed "
                f"reason=permission_denied user_id={user_id} owner_id={image.user_id}"
            )
            raise PermissionDeniedException(detail="You do not own this image")

        file_hash = image.file_hash

        # We need to know the path to delete the file.
        # Assuming we can get it from the file relation or reconstruct it.
        # For now, let's try to find it with extension or without.
        # Ideally, we should fetch 'file' relation with 'path'.

        # Since we don't have the file object here easily without extra query (unless image.file is loaded),
        # we will try to resolve path.
        # But wait, image.file should be loaded if we use joinedload in repo.

        # Let's assume image.file is available or we query it.
        # For simplicity in this fix, I will try to find the file on disk.

        # Remove user link
        await self.repository.delete_image(image_id)

        # Garbage Collection Check
        usage_count = await self.repository.get_usage_count(file_hash)

        if usage_count == 0:
            logger.info(f"MediaService | action=gc_start hash={file_hash}")

            await self.repository.delete_file(file_hash)

            # Try to find file with extension
            found = False
            for ext in [""] + list(self.ALLOWED_MIME_TYPES.values()):
                path = self._get_storage_path(file_hash, ext)
                if path.exists():
                    await self._remove_file(path)
                    found = True

            thumb_path = self._get_thumbnail_path(file_hash)
            await self._remove_file(thumb_path)

            if found:
                logger.info(f"MediaService | action=gc_success hash={file_hash}")
            else:
                logger.warning(f"MediaService | action=gc_warn reason=file_not_found_on_disk hash={file_hash}")

        await self.repository.commit()
        logger.info(f"MediaService | action=delete_success image_id={image_id} user_id={user_id}")

    def get_original_file(self, file_hash: str) -> Path:
        """
        Get path to original file.
        Used for fallback serving via Python.
        """
        # Try without extension first (legacy)
        path = self._get_storage_path(file_hash)
        if path.exists():
            return path

        # Try with extensions
        for ext in self.ALLOWED_MIME_TYPES.values():
            path = self._get_storage_path(file_hash, ext)
            if path.exists():
                return path

        logger.warning(f"MediaService | action=get_file_failed reason=not_found hash={file_hash}")
        raise NotFoundException(detail="File not found")

    def get_thumbnail_file(self, file_hash: str) -> Path:
        """
        Get path to thumbnail file.
        """
        path = self._get_thumbnail_path(file_hash)
        if not path.exists():
            logger.warning(f"MediaService | action=get_thumb_failed reason=not_found hash={file_hash}")
            raise NotFoundException(detail="Thumbnail not found")
        return path

    # --- Private Helpers ---

    async def _process_stream_to_temp(self, upload_file: UploadFile, temp_path: Path) -> tuple[str, int]:
        """
        Reads UploadFile stream, calculates SHA256, and writes to temp_path simultaneously.
        Enforces MAX_UPLOAD_SIZE.
        Returns: (hex_hash, size_bytes)
        """
        sha256 = hashlib.sha256()
        size = 0

        # Use str(temp_path) for aiofiles compatibility
        async with aiofiles.open(temp_path, "wb") as out_file:
            while True:
                chunk = await upload_file.read(self.chunk_size)
                if not chunk:
                    break

                size += len(chunk)
                if size > self.max_upload_size:
                    logger.warning(
                        f"MediaService | action=upload_rejected "
                        f"reason=size_limit size={size} limit={self.max_upload_size}"
                    )
                    raise ValidationException(detail=f"File too large. Max size is {self.max_upload_size} bytes.")

                sha256.update(chunk)
                await out_file.write(chunk)

        return sha256.hexdigest(), size

    async def _validate_file_type(self, path: Path) -> str:
        """
        Validates file type using python-magic (libmagic).
        Returns detected mime-type if allowed, raises ValidationException otherwise.
        """

        def _get_mime() -> str:
            return str(magic.from_file(str(path), mime=True))

        detected_mime = await run_in_threadpool(_get_mime)

        if detected_mime not in self.ALLOWED_MIME_TYPES:
            logger.warning(f"MediaService | action=upload_rejected reason=invalid_mime mime={detected_mime}")
            raise ValidationException(
                detail=f"Invalid file type: {detected_mime}. Allowed: {', '.join(self.ALLOWED_MIME_TYPES.keys())}"
            )

        return detected_mime

    def _get_storage_path(self, file_hash: str, ext: str = "") -> Path:
        """
        Generate sharded path: root/storage/a1/b2/a1b2c3d4...ext
        Creates directories if needed.
        """
        # Sharding: a1/b2
        shard = self.storage_dir / file_hash[:2] / file_hash[2:4]
        os.makedirs(shard, exist_ok=True)
        return shard / f"{file_hash}{ext}"

    def _get_thumbnail_path(self, file_hash: str) -> Path:
        """
        Generate path for thumbnail: root/storage/a1/b2/a1b2c3d4..._thumb.jpg
        """
        # Thumbnails are always jpg and stored alongside original
        # We use _get_storage_path just to get the dir, but we construct filename manually
        shard = self.storage_dir / file_hash[:2] / file_hash[2:4]
        return shard / f"{file_hash}_thumb.jpg"

    async def _generate_thumbnail(self, original_path: Path, file_hash: str) -> None:
        """
        Generates a thumbnail for the image using Pillow.
        Runs in a threadpool to avoid blocking the event loop.
        """
        thumb_path = self._get_thumbnail_path(file_hash)

        def _process() -> None:
            with PILImage.open(original_path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")  # type: ignore

                img.thumbnail((300, 300))
                img.save(thumb_path, "JPEG", quality=85)

        await run_in_threadpool(_process)
        logger.debug(f"MediaService | action=thumbnail_generated hash={file_hash}")

    @staticmethod
    async def _remove_file(path: Path) -> None:
        """
        Async wrapper for removing file using aiofiles.os
        """
        if path.exists():
            await aios.remove(path)
