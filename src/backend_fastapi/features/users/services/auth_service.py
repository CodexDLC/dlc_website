import secrets
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy.exc import IntegrityError

from src.backend_fastapi.core.config import settings
from src.backend_fastapi.core.exceptions import AuthException, BusinessLogicException
from src.backend_fastapi.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from src.backend_fastapi.features.users.contracts.token_repository import ITokenRepository
from src.backend_fastapi.features.users.contracts.user_repository import IUserRepository
from src.backend_fastapi.features.users.schemas.auth_token import Token
from src.backend_fastapi.features.users.schemas.user import UserCreate, UserResponse


class AuthService:
    """
    Service responsible for Authentication logic.
    Handles registration, login, and token management.
    """

    def __init__(self, user_repository: IUserRepository, token_repository: ITokenRepository):
        self.user_repository = user_repository
        self.token_repository = token_repository

    async def register_user(self, user_in: UserCreate) -> UserResponse:
        """
        Register a new user.
        """
        logger.info(f"AuthService | action=register_attempt email={user_in.email}")

        hashed_password = get_password_hash(user_in.password)
        user_with_hash = user_in.model_copy(update={"password": hashed_password})

        try:
            created_user = await self.user_repository.create(user_with_hash)
            await self.user_repository.commit()
        except IntegrityError:
            logger.warning(
                f"AuthService | action=register_failed reason=email_exists_race_condition email={user_in.email}"
            )
            raise BusinessLogicException(detail="User with this email already exists") from None

        logger.info(f"AuthService | action=register_success user_id={created_user.id}")

        return UserResponse.model_validate(created_user)

    async def authenticate_user(self, email: str, password: str) -> UserResponse | None:
        """
        Authenticate a user by email and password.
        Returns UserResponse if successful, None otherwise.
        """
        logger.info(f"AuthService | action=auth_attempt email={email}")

        user = await self.user_repository.get_by_email(email)
        if not user:
            logger.warning(f"AuthService | action=auth_failed reason=user_not_found email={email}")
            return None

        if not verify_password(password, user.hashed_password):
            logger.warning(f"AuthService | action=auth_failed reason=invalid_password email={email}")
            return None

        if not user.is_active:
            logger.warning(f"AuthService | action=auth_failed reason=inactive_user email={email}")
            return None

        logger.info(f"AuthService | action=auth_success user_id={user.id}")
        return UserResponse.model_validate(user)

    async def create_tokens(self, user: UserResponse) -> Token:
        """
        Generate Access and Refresh tokens for a user.
        Saves the refresh token in the database.
        """
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(subject=str(user.id), expires_delta=access_token_expires)

        refresh_token = secrets.token_urlsafe(32)
        refresh_token_expires = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await self.token_repository.create(user_id=user.id, token=refresh_token, expires_at=refresh_token_expires)
        await self.token_repository.commit()

        logger.debug(f"AuthService | action=tokens_generated user_id={user.id}")

        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    async def refresh_token(self, token: str) -> Token:
        """
        Rotate refresh token: validate old one, delete it, create new pair.
        """
        db_token = await self.token_repository.get_by_token(token)
        if not db_token:
            logger.warning("AuthService | action=refresh_failed reason=token_not_found")
            raise AuthException("Invalid refresh token")

        now = datetime.now(UTC)
        if db_token.expires_at < now:
            logger.warning("AuthService | action=refresh_failed reason=token_expired")
            await self.token_repository.delete(token)
            await self.token_repository.commit()
            raise AuthException("Refresh token expired")

        user = await self.user_repository.get_by_id(db_token.user_id)
        if not user:
            logger.error(f"AuthService | action=refresh_failed reason=user_not_found user_id={db_token.user_id}")
            await self.token_repository.delete(token)
            await self.token_repository.commit()
            raise AuthException("User not found")

        if not user.is_active:
            raise AuthException("User is inactive")

        await self.token_repository.delete(token)

        user_schema = UserResponse.model_validate(user)
        return await self.create_tokens(user_schema)

    async def logout(self, token: str) -> None:
        """
        Logout: simply delete the refresh token.
        """
        await self.token_repository.delete(token)
        await self.token_repository.commit()
