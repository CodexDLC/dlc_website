import uuid
from typing import Protocol

from src.backend_fastapi.database.models import User
from src.backend_fastapi.features.users.schemas.user import UserCreate


class IUserRepository(Protocol):
    """
    Interface for User Repository.
    Defines the contract for data access operations related to Users.
    """

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """
        Retrieve a user by their unique ID.

        Args:
            user_id: The UUID of the user.

        Returns:
            User object if found, None otherwise.
        """
        ...

    async def get_by_email(self, email: str) -> User | None:
        """
        Retrieve a user by their email address.

        Args:
            email: The email address to search for.

        Returns:
            User object if found, None otherwise.
        """
        ...

    async def create(self, user_in: UserCreate) -> User:
        """
        Create a new user in the database.

        Args:
            user_in: Data required to create a user.

        Returns:
            The created User object.
        """
        ...

    async def commit(self) -> None:
        """
        Commit the current transaction.
        """
        ...
