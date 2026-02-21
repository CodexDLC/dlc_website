import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend_fastapi.database.models import User
from src.backend_fastapi.features.users.schemas.user import UserCreate


class UserRepository:
    """
    SQLAlchemy implementation of IUserRepository.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """
        Retrieve a user by their unique ID.
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        Retrieve a user by their email address.
        """
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user_in: UserCreate) -> User:
        """
        Create a new user in the database.
        Note: user_in.password must be already HASHED by the logic layer.
        """
        db_user = User(
            email=user_in.email,
            hashed_password=user_in.password,
            is_active=True,
            is_superuser=False,
        )
        self.session.add(db_user)
        await self.session.flush()
        await self.session.refresh(db_user)
        return db_user

    async def commit(self) -> None:
        await self.session.commit()
