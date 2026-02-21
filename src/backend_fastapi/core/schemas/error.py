from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetails(BaseModel):
    """
    Detailed information about the error.
    """

    code: str = Field(..., description="Internal error code (e.g. 'user_not_found')")
    message: str = Field(..., description="Human-readable error message")
    fields: list[Any] | None = Field(None, description="List of validation errors (for 422)")

    model_config = ConfigDict(extra="allow")


class ErrorResponse(BaseModel):
    """
    Standardized error response structure.
    Used for Swagger documentation (400, 401, 403, 404, 500).
    """

    error: ErrorDetails
