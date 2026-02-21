from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.backend_fastapi.core.exceptions import AuthException, BusinessLogicException
from src.backend_fastapi.database.models.users import User
from src.backend_fastapi.features.users.contracts.token_repository import ITokenRepository
from src.backend_fastapi.features.users.contracts.user_repository import IUserRepository
from src.backend_fastapi.features.users.schemas.user import UserCreate
from src.backend_fastapi.features.users.services.auth_service import AuthService

# --- Mocks ---


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    repo = AsyncMock(spec=IUserRepository)
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def mock_token_repo() -> AsyncMock:
    repo = AsyncMock(spec=ITokenRepository)
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def auth_service(mock_user_repo: AsyncMock, mock_token_repo: AsyncMock) -> AuthService:
    return AuthService(mock_user_repo, mock_token_repo)


# --- Tests ---


@pytest.mark.asyncio
async def test_register_success(auth_service: AuthService, mock_user_repo: AsyncMock) -> None:
    # Arrange
    user_in = UserCreate(email="test@example.com", password="password123")
    mock_user_repo.get_by_email.return_value = None

    # FIX: Use real object with all required fields for Pydantic validation
    created_user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed_pw",
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(UTC),
    )
    mock_user_repo.create.return_value = created_user

    # Act
    result = await auth_service.register_user(user_in)

    # Assert
    assert result.email == "test@example.com"
    mock_user_repo.create.assert_called_once()
    mock_user_repo.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_duplicate_email(auth_service: AuthService, mock_user_repo: AsyncMock) -> None:
    # Arrange
    user_in = UserCreate(email="exist@example.com", password="password123")

    # Simulate DB IntegrityError on create or commit
    # Since the logic calls create then commit, we can raise it on create for simplicity
    # or on commit if create just adds to session.
    # In async SQLAlchemy, create usually just adds, commit flushes.
    # But let's look at the logic: it calls create, then commit.
    # We'll raise on create to be safe, or commit.
    mock_user_repo.create.side_effect = IntegrityError(None, None, Exception("Duplicate"))

    # Act & Assert
    with pytest.raises(BusinessLogicException) as exc:
        await auth_service.register_user(user_in)

    assert "already exists" in str(exc.value)
    # Verify create WAS called (attempted)
    mock_user_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_authenticate_success(auth_service: AuthService, mock_user_repo: AsyncMock) -> None:
    # Arrange
    from src.backend_fastapi.core.security import get_password_hash

    hashed = get_password_hash("password123")

    # FIX: Use real object
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password=hashed,
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(UTC),
    )
    mock_user_repo.get_by_email.return_value = user

    # Act
    result = await auth_service.authenticate_user("test@example.com", "password123")

    # Assert
    assert result is not None
    assert result.email == "test@example.com"


@pytest.mark.asyncio
async def test_authenticate_wrong_password(auth_service: AuthService, mock_user_repo: AsyncMock) -> None:
    # Arrange
    from src.backend_fastapi.core.security import get_password_hash

    hashed = get_password_hash("password123")
    user = User(id=uuid4(), email="test@example.com", hashed_password=hashed, is_active=True)
    mock_user_repo.get_by_email.return_value = user

    # Act
    result = await auth_service.authenticate_user("test@example.com", "wrongpass")

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_refresh_token_success(
    auth_service: AuthService, mock_token_repo: AsyncMock, mock_user_repo: AsyncMock
) -> None:
    # Arrange
    valid_token = MagicMock()
    valid_token.expires_at = datetime.now(UTC) + timedelta(days=1)
    valid_token.user_id = uuid4()

    mock_token_repo.get_by_token.return_value = valid_token

    # FIX: Use real object
    user = User(
        id=valid_token.user_id,
        email="test@example.com",
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(UTC),
        hashed_password="hash",
    )
    mock_user_repo.get_by_id.return_value = user

    # Act
    result = await auth_service.refresh_token("some_refresh_token")

    # Assert
    assert result.access_token is not None
    assert result.refresh_token is not None
    mock_token_repo.delete.assert_called_with("some_refresh_token")
    mock_token_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_token_expired(auth_service: AuthService, mock_token_repo: AsyncMock) -> None:
    # Arrange
    expired_token = MagicMock()
    expired_token.expires_at = datetime.now(UTC) - timedelta(days=1)  # Expired

    mock_token_repo.get_by_token.return_value = expired_token

    # Act & Assert
    with pytest.raises(AuthException) as exc:
        await auth_service.refresh_token("expired_token")

    assert "expired" in str(exc.value)
    mock_token_repo.delete.assert_called_with("expired_token")
