import uuid
from datetime import datetime
from typing import Protocol

from src.backend_fastapi.database.models import RefreshToken


class ITokenRepository(Protocol):
    """
    Interface for Refresh Token Repository.
    """

    async def create(self, user_id: uuid.UUID, token: str, expires_at: datetime) -> RefreshToken:
        """
        Save a new refresh token.
        """
        ...

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """
        Find a refresh token by its value.
        """
        ...

    async def delete(self, token: str) -> None:
        """
        Delete a specific token (logout/rotation).
        """
        ...

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """
        Delete all tokens for a user (logout from all devices).
        """
        ...

    async def commit(self) -> None:
        """
        Commit the current transaction.
        """
        ...
