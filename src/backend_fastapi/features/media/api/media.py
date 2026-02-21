from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi import Path as PathParam
from fastapi.responses import FileResponse
from loguru import logger

from src.backend_fastapi.database.models import User
from src.backend_fastapi.dependencies.auth import get_current_user
from src.backend_fastapi.dependencies.media import get_media_service
from src.backend_fastapi.features.media.schemas.media import ImageRead
from src.backend_fastapi.features.media.services.media_service import MediaService

router = APIRouter()


@router.post("/upload", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
) -> ImageRead:
    """
    Upload a new image.

    Returns:
        ImageRead: Uploaded image metadata.
    """
    logger.info(f"MediaRouter | action=upload_request user_id={current_user.id} filename={file.filename}")
    return await service.upload_image(user_id=current_user.id, file=file)


@router.get("/feed", response_model=list[ImageRead])
async def get_feed(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: MediaService = Depends(get_media_service),
) -> list[ImageRead]:
    """
    Get public feed of images.

    Returns:
        list[ImageRead]: List of public images.
    """
    logger.info(f"MediaRouter | action=feed_request limit={limit} offset={offset}")
    return await service.get_feed(limit=limit, offset=offset)


@router.get("/my", response_model=list[ImageRead])
async def get_my_gallery(
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: MediaService = Depends(get_media_service),
) -> list[ImageRead]:
    """
    Get current user's gallery.

    Returns:
        list[ImageRead]: List of user's images.
    """
    logger.info(f"MediaRouter | action=my_gallery_request user_id={current_user.id} limit={limit} offset={offset}")
    return await service.get_user_gallery(user_id=current_user.id, limit=limit, offset=offset)


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: UUID = PathParam(...),
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
) -> None:
    """
    Delete an image.
    """
    logger.info(f"MediaRouter | action=delete_request user_id={current_user.id} image_id={image_id}")
    await service.delete_image(user_id=current_user.id, image_id=image_id)


# --- Serving Files (Dev Mode / Fallback) ---


@router.get("/{file_hash}", response_class=FileResponse)
async def get_file(
    file_hash: str = PathParam(..., min_length=64, max_length=64),
    service: MediaService = Depends(get_media_service),
) -> FileResponse:
    """
    Serve original file by hash.
    """
    # Use public logic method to resolve path
    path = service.get_original_file(file_hash)
    logger.debug(f"MediaRouter | action=serve_file hash={file_hash}")
    return FileResponse(path)


@router.get("/{file_hash}/thumb", response_class=FileResponse)
async def get_thumbnail(
    file_hash: str = PathParam(..., min_length=64, max_length=64),
    service: MediaService = Depends(get_media_service),
) -> FileResponse:
    """
    Serve thumbnail by hash.
    """
    # Use public logic method to resolve path
    path = service.get_thumbnail_file(file_hash)
    logger.debug(f"MediaRouter | action=serve_thumb hash={file_hash}")
    return FileResponse(path)
