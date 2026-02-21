import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from src.backend_fastapi.core.schemas.base import BaseRequest, BaseResponse


class UserBase(BaseModel):
    """
    Base schema for User data.
    Shared properties.
    """

    email: EmailStr


class UserCreate(UserBase, BaseRequest):
    """
    Schema for User registration.
    """

    password: str = Field(..., min_length=8, description="User password")


class UserUpdate(BaseRequest):
    """
    Schema for User update.
    """

    email: EmailStr | None = None
    password: str | None = None
    is_active: bool | None = None


class UserResponse(UserBase, BaseResponse):
    """
    Schema for User response (public data).
    """

    id: uuid.UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
