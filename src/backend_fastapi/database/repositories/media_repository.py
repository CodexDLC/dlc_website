from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend_fastapi.database.models import File, Image


class MediaRepository:
    """
    SQLAlchemy implementation of IMediaRepository (Protocol).
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- File Operations (CAS) ---

    async def get_file_by_hash(self, file_hash: str) -> File | None:
        """
        Check if a file with this hash already exists (Deduplication).
        """
        stmt = select(File).where(File.hash == file_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_file(self, file_hash: str, size_bytes: int, mime_type: str, path: str) -> File:
        """
        Register a new physical file in the database.
        Initial ref_count is 0 (will be incremented when Image is created).
        """
        file = File(
            hash=file_hash,
            size_bytes=size_bytes,
            mime_type=mime_type,
            path=path,
            ref_count=0,
        )
        self.session.add(file)
        await self.session.flush()
        return file

    async def delete_file(self, file_hash: str) -> None:
        """
        Delete physical file record (used by GC).
        """
        stmt = delete(File).where(File.hash == file_hash)
        await self.session.execute(stmt)

    async def get_usage_count(self, file_hash: str) -> int:
        """
        Get current reference count from the file record.
        """
        stmt = select(File.ref_count).where(File.hash == file_hash)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # --- Image Operations (User Assets) ---

    async def create_image(self, user_id: UUID, file_hash: str, filename: str) -> Image:
        """
        Link a user to a file (create an asset).
        Increments the file's ref_count.
        """
        # 1. Create Image record
        image = Image(user_id=user_id, file_hash=file_hash, filename=filename)
        self.session.add(image)

        # 2. Increment File ref_count
        stmt = update(File).where(File.hash == file_hash).values(ref_count=File.ref_count + 1)
        await self.session.execute(stmt)

        await self.session.flush()
        await self.session.refresh(image)

        # Explicitly load the file relationship to avoid lazy loading issues later
        stmt_load = select(Image).where(Image.id == image.id).options(selectinload(Image.file))
        result = await self.session.execute(stmt_load)
        return result.scalar_one()

    async def get_image_by_id(self, image_id: UUID) -> Image | None:
        """
        Get image metadata by ID.
        """
        stmt = (
            select(Image).where(Image.id == image_id).options(selectinload(Image.file))  # Eager load File
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_public_images(self, limit: int, offset: int) -> list[Image]:
        """
        Get gallery for public feed.
        """
        stmt = (
            select(Image)
            .order_by(Image.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(Image.file))  # Eager load File
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_images_by_user(self, user_id: UUID, limit: int, offset: int) -> list[Image]:
        """
        Get gallery for a specific user.
        """
        stmt = (
            select(Image)
            .where(Image.user_id == user_id)
            .order_by(Image.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(Image.file))  # Eager load File
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_image(self, image_id: UUID) -> None:
        """
        Delete user image (asset).
        Decrements the file's ref_count.
        """
        # 1. Get file_hash before deleting (to know which file to decrement)
        stmt_get = select(Image.file_hash).where(Image.id == image_id)
        result = await self.session.execute(stmt_get)
        file_hash = result.scalar_one_or_none()

        if file_hash:
            # 2. Decrement File ref_count
            stmt_update = update(File).where(File.hash == file_hash).values(ref_count=File.ref_count - 1)
            await self.session.execute(stmt_update)

        # 3. Delete Image
        stmt_del = delete(Image).where(Image.id == image_id)
        await self.session.execute(stmt_del)

    async def commit(self) -> None:
        await self.session.commit()
