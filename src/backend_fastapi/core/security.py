from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt
from loguru import logger
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """
    Creates a JWT access token.

    Args:
        subject: The subject of the token (usually user_id).
        expires_delta: Optional expiration time delta.

    Returns:
        str: Encoded JWT token.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject)}

    try:
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return str(encoded_jwt)
    except Exception as exc:
        logger.error(f"Security | action=create_token_failed error={exc}")
        raise exc


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password.
    """
    return bool(pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """
    Hashes a password using bcrypt.
    """
    return str(pwd_context.hash(password))
