import uuid
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend_fastapi.core.config import settings
from src.backend_fastapi.core.database import get_db
from src.backend_fastapi.core.exceptions import AuthException
from src.backend_fastapi.core.security import ALGORITHM
from src.backend_fastapi.database.models import User
from src.backend_fastapi.database.repositories.token_repository import TokenRepository
from src.backend_fastapi.database.repositories.user_repository import UserRepository
from src.backend_fastapi.features.users.contracts.token_repository import ITokenRepository
from src.backend_fastapi.features.users.contracts.user_repository import IUserRepository
from src.backend_fastapi.features.users.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IUserRepository:
    """
    Dependency provider for User Repository.
    """
    return UserRepository(session=db)


def get_token_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ITokenRepository:
    """
    Dependency provider for Token Repository.
    """
    return TokenRepository(session=db)


def get_auth_service(
    user_repository: Annotated[IUserRepository, Depends(get_user_repository)],
    token_repository: Annotated[ITokenRepository, Depends(get_token_repository)],
) -> AuthService:
    """
    Dependency provider for Auth Service.
    """
    return AuthService(user_repository=user_repository, token_repository=token_repository)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    Validates token signature and expiration.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id_raw: Any = payload.get("sub")

        if user_id_raw is None:
            logger.warning("AuthDependency | action=validate_failed reason=missing_sub")
            raise AuthException(detail="Could not validate credentials")

        user_id_str = str(user_id_raw)

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError as exc:
            logger.warning(f"AuthDependency | action=validate_failed reason=invalid_uuid sub={user_id_str}")
            raise AuthException(detail="Invalid token subject") from exc

    except JWTError as exc:
        logger.warning(f"AuthDependency | action=validate_failed reason=jwt_error error={exc}")
        raise AuthException(detail="Could not validate credentials") from exc

    user = await auth_service.user_repository.get_by_id(user_id=user_id)
    if user is None:
        logger.warning(f"AuthDependency | action=user_lookup_failed reason=not_found user_id={user_id}")
        raise AuthException(detail="User not found")

    return user
