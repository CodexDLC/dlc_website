from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.backend_fastapi.core.exceptions import PermissionDeniedException
from src.backend_fastapi.database.models.media import File, Image
from src.backend_fastapi.features.media.contracts.media_repository import IMediaRepository
from src.backend_fastapi.features.media.services.media_service import MediaService

# --- Mocks ---


@pytest.fixture
def mock_media_repo() -> AsyncMock:
    repo = AsyncMock(spec=IMediaRepository)
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def media_service(mock_media_repo: AsyncMock) -> MediaService:
    # Mock settings inside logic
    with patch("src.backend_fastapi.features.media.services.media_service.settings") as mock_settings:
        mock_settings.MAX_UPLOAD_SIZE = 1024 * 1024  # 1MB
        mock_settings.UPLOAD_DIR = Path("/tmp/test_uploads")

        service = MediaService(mock_media_repo)
        # Override dirs to avoid real FS creation in init
        service.temp_dir = MagicMock()
        service.storage_dir = MagicMock()
        return service


# --- Tests ---


@pytest.mark.asyncio
async def test_upload_image_new_file(media_service: MediaService, mock_media_repo: AsyncMock) -> None:
    """
    Test uploading a new file (Deduplication MISS).
    Should create File and Image records and move file to storage.
    """
    # Arrange
    user_id = uuid4()
    file_mock = AsyncMock()
    file_mock.filename = "cat.jpg"
    file_mock.read.side_effect = [b"fake_image_bytes", b""]  # Simulate stream

    # Mock internal helpers
    media_service._process_stream_to_temp = AsyncMock(return_value=("hash123", 100))  # type: ignore
    media_service._validate_file_type = AsyncMock(return_value="image/jpeg")  # type: ignore
    media_service._remove_file = AsyncMock()  # type: ignore
    media_service._get_storage_path = MagicMock(return_value=Path("/storage/hash123.jpg"))  # type: ignore
    media_service._generate_thumbnail = AsyncMock()  # type: ignore

    # Mock repo behavior (Deduplication MISS)
    mock_media_repo.get_file_by_hash.return_value = None

    mock_file = File(
        hash="hash123",
        size_bytes=100,
        mime_type="image/jpeg",
        path="/storage/hash123.jpg",
        created_at=datetime.now(UTC),
    )
    mock_image = Image(
        id=uuid4(),
        user_id=user_id,
        file_hash="hash123",
        filename="cat.jpg",
        created_at=datetime.now(UTC),
        file=mock_file,
    )
    mock_media_repo.create_image.return_value = mock_image

    # Mock shutil.move
    with patch("shutil.move") as mock_move:
        # Act
        result = await media_service.upload_image(user_id, file_mock)

    # Assert
    assert result.file.hash == "hash123"
    mock_move.assert_called_once()  # Should move file
    mock_media_repo.create_file.assert_called_once()
    mock_media_repo.create_image.assert_called_once()


@pytest.mark.asyncio
async def test_upload_image_deduplication_hit(media_service: MediaService, mock_media_repo: AsyncMock) -> None:
    """
    Test uploading an existing file (Deduplication HIT).
    Should NOT create File record, only Image record.
    """
    # Arrange
    user_id = uuid4()
    file_mock = AsyncMock()
    file_mock.filename = "cat_copy.jpg"

    media_service._process_stream_to_temp = AsyncMock(return_value=("hash123", 100))  # type: ignore
    media_service._validate_file_type = AsyncMock(return_value="image/jpeg")  # type: ignore
    media_service._remove_file = AsyncMock()  # type: ignore

    # Mock repo behavior (Deduplication HIT)
    existing_file = File(
        hash="hash123",
        size_bytes=100,
        mime_type="image/jpeg",
        path="/storage/hash123.jpg",
        created_at=datetime.now(UTC),
    )
    mock_media_repo.get_file_by_hash.return_value = existing_file

    mock_image = Image(
        id=uuid4(),
        user_id=user_id,
        file_hash="hash123",
        filename="cat_copy.jpg",
        created_at=datetime.now(UTC),
        file=existing_file,
    )
    mock_media_repo.create_image.return_value = mock_image

    with patch("shutil.move") as mock_move:
        # Act
        result = await media_service.upload_image(user_id, file_mock)

    # Assert
    assert result.file.hash == "hash123"
    mock_move.assert_not_called()  # Should NOT move file
    mock_media_repo.create_file.assert_not_called()  # Should NOT create new file record
    mock_media_repo.create_image.assert_called_once()  # But SHOULD create user link
    media_service._remove_file.assert_called()  # Should remove temp file


@pytest.mark.asyncio
async def test_delete_image_owner_success(media_service: MediaService, mock_media_repo: AsyncMock) -> None:
    """
    Test deleting image by owner.
    GC should NOT trigger if file is used by others.
    """
    # Arrange
    user_id = uuid4()
    image_id = uuid4()

    image = MagicMock()
    image.user_id = user_id
    image.file_hash = "hash123"
    mock_media_repo.get_image_by_id.return_value = image

    # GC: File is still used by others
    mock_media_repo.get_usage_count.return_value = 2

    # Act
    await media_service.delete_image(user_id, image_id)

    # Assert
    mock_media_repo.delete_image.assert_called_with(image_id)
    mock_media_repo.delete_file.assert_not_called()  # Should NOT delete physical file


@pytest.mark.asyncio
async def test_delete_image_gc_trigger(media_service: MediaService, mock_media_repo: AsyncMock) -> None:
    """
    Test deleting image triggering Garbage Collection.
    """
    # Arrange
    user_id = uuid4()
    image_id = uuid4()

    image = MagicMock()
    image.user_id = user_id
    image.file_hash = "hash123"
    mock_media_repo.get_image_by_id.return_value = image

    # GC: File is NOT used anymore
    mock_media_repo.get_usage_count.return_value = 0

    media_service._remove_file = AsyncMock()  # type: ignore

    # Mock _get_storage_path to return a Path that "exists"
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True  # Simulate file exists
    media_service._get_storage_path = MagicMock(return_value=mock_path)  # type: ignore

    media_service._get_thumbnail_path = MagicMock(return_value=Path("/thumb"))  # type: ignore

    # Act
    await media_service.delete_image(user_id, image_id)

    # Assert
    mock_media_repo.delete_image.assert_called_with(image_id)
    mock_media_repo.delete_file.assert_called_with("hash123")  # Should delete physical file

    # We expect at least 2 calls (one for original, one for thumb)
    # Since we iterate over extensions, it might be called more if multiple extensions match (unlikely in test)
    # But we mocked exists=True for ALL calls to _get_storage_path.
    # The loop iterates 5 times (empty + 4 mime types).
    # So if exists=True always, it will try to remove 5 times + 1 thumb = 6 times.

    # Let's adjust the mock to only return True for one specific extension to be precise.
    # Or just assert call_count >= 2
    assert media_service._remove_file.call_count >= 2


@pytest.mark.asyncio
async def test_delete_image_not_owner(media_service: MediaService, mock_media_repo: AsyncMock) -> None:
    """
    Test deleting image by non-owner (Permission Denied).
    """
    # Arrange
    user_id = uuid4()
    other_user_id = uuid4()
    image_id = uuid4()

    image = MagicMock()
    image.user_id = other_user_id  # Owner is different
    mock_media_repo.get_image_by_id.return_value = image

    # Act & Assert
    with pytest.raises(PermissionDeniedException):
        await media_service.delete_image(user_id, image_id)
