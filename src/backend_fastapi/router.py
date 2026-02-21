# backend/router.py
from fastapi import APIRouter

from src.backend_fastapi.features.media.api.media import router as media_router
from src.backend_fastapi.features.users.api.auth import router as auth_router
from src.backend_fastapi.features.users.api.users import router as users_router

api_router = APIRouter()

# Описание тегов для Swagger
tags_metadata = [
    {
        "name": "System",
        "description": "Health check and logic info.",
    },
    {
        "name": "Auth",
        "description": "Authentication: **register**, **login**, **refresh**.",
    },
    {
        "name": "Users",
        "description": "Operations with users: **profile**.",
    },
    {
        "name": "Media",
        "description": "Media management: **upload**, **gallery**, **processing**.",
    },
]

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(media_router, prefix="/media", tags=["Media"])
