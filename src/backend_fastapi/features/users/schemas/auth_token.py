from pydantic import BaseModel

from src.backend_fastapi.core.schemas.base import BaseRequest, BaseResponse


class Token(BaseResponse):
    """
    Schema for JWT Token response.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    Schema for JWT Token payload.
    Internal use only, no need for BaseRequest/Response.
    """

    sub: str | None = None
    exp: int | None = None


class RefreshTokenRequest(BaseRequest):
    """
    Schema for Refresh Token request.
    """

    refresh_token: str
