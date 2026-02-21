import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend_fastapi.database.models import RefreshToken


class TokenRepository:
    """
    SQLAlchemy implementation of ITokenRepository.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: uuid.UUID, token: str, expires_at: datetime) -> RefreshToken:
        """
        Create a new refresh token.
        """
        db_token = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
        self.session.add(db_token)
        await self.session.flush()
        await self.session.refresh(db_token)
        return db_token

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """
        Retrieve a refresh token by its value.
        """
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, token: str) -> None:
        """
        Delete a specific refresh token.
        """
        stmt = delete(RefreshToken).where(RefreshToken.token == token)
        await self.session.execute(stmt)

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """
        Delete all refresh tokens for a specific user (e.g. logout all devices).
        """
        stmt = delete(RefreshToken).where(RefreshToken.user_id == user_id)
        await self.session.execute(stmt)

    async def commit(self) -> None:
        await self.session.commit()
