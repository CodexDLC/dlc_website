from fastapi import APIRouter, Depends
from loguru import logger

from src.backend_fastapi.database.models import User
from src.backend_fastapi.dependencies.auth import get_current_user
from src.backend_fastapi.features.users.schemas.user import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current authenticated user profile.

    Returns:
        User: User object (converted to UserResponse).
    """
    logger.info(f"UserRouter | action=get_me user_id={current_user.id}")
    return current_user
