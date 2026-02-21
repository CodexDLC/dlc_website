from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend_fastapi.core.database import get_db
from src.backend_fastapi.database.repositories.media_repository import MediaRepository
from src.backend_fastapi.features.media.contracts.media_repository import IMediaRepository
from src.backend_fastapi.features.media.services.media_service import MediaService


def get_media_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IMediaRepository:
    """
    Dependency provider for Media Repository.
    """
    return MediaRepository(session=db)


def get_media_service(
    repository: Annotated[IMediaRepository, Depends(get_media_repository)],
) -> MediaService:
    """
    Dependency provider for Media Service.
    """
    return MediaService(repository=repository)
