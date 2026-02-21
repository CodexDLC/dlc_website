from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger

from src.backend_fastapi.core.exceptions import AuthException
from src.backend_fastapi.dependencies.auth import get_auth_service
from src.backend_fastapi.features.users.schemas.auth_token import RefreshTokenRequest, Token
from src.backend_fastapi.features.users.schemas.user import UserCreate, UserResponse
from src.backend_fastapi.features.users.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_new_user(user_in: UserCreate, auth_service: AuthService = Depends(get_auth_service)) -> UserResponse:
    """
    Register a new user.

    Returns:
        UserResponse: Created user data.
    """
    logger.info(f"AuthRouter | action=register_request email={user_in.email}")
    return await auth_service.register_user(user_in)


@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    """
    Authenticate user (OAuth2 Password Flow).

    Returns:
        Token: Access and refresh token pair.
    """
    logger.info(f"AuthRouter | action=login_request email={form_data.username}")

    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"AuthRouter | action=login_failed reason=invalid_credentials email={form_data.username}")
        raise AuthException(detail="Incorrect email or password")

    tokens = await auth_service.create_tokens(user)
    logger.info(f"AuthRouter | action=login_success user_id={user.id}")

    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(token_in: RefreshTokenRequest, auth_service: AuthService = Depends(get_auth_service)) -> Token:
    """
    Refresh access token using refresh token.

    Returns:
        Token: New token pair.
    """
    logger.info("AuthRouter | action=refresh_request")
    return await auth_service.refresh_token(token_in.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(token_in: RefreshTokenRequest, auth_service: AuthService = Depends(get_auth_service)) -> Response:
    """
    Logout user (invalidate refresh token).
    """
    logger.info("AuthRouter | action=logout_request")
    await auth_service.logout(token_in.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
