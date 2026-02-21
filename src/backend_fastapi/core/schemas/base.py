from pydantic import BaseModel, ConfigDict


class BaseRequest(BaseModel):
    """
    Base schema for incoming request data (Request Body).
    Used for validation of client input.
    """

    model_config = ConfigDict(populate_by_name=True)


class BaseResponse(BaseModel):
    """
    Base schema for outgoing response data (Response Body).
    Configured to support ORM objects (from_attributes=True).
    """

    model_config = ConfigDict(from_attributes=True)
