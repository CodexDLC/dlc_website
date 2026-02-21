# backend/main.py
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .core.config import settings
from .core.database import async_engine
from .core.exceptions import BaseAPIException, api_exception_handler
from .core.logger import setup_loguru
from .core.schemas.error import ErrorResponse
from .router import api_router, tags_metadata


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    setup_loguru()
    logger.info("🚀 Server starting... Project: {name}", name=settings.PROJECT_NAME)

    if settings.DEBUG:
        logger.debug("🐛 Debug mode is ENABLED")
    else:
        logger.info("🔒 Production mode: Swagger UI is DISABLED")

    # Migrations are handled via CLI or CD pipeline, not at startup.
    # This avoids race conditions when running multiple replicas.
    # Run manually: alembic upgrade head
    # Or in CD:     docker run --rm app alembic upgrade head
    logger.info("💡 Migrations: run 'alembic upgrade head' before deploying.")

    yield

    logger.info("🛑 Server shutting down... Closing DB connections...")
    await async_engine.dispose()
    logger.info("👋 Bye!")


# --- DOCS CONFIGURATION ---
docs_url = "/docs" if settings.DEBUG else None
redoc_url = "/redoc" if settings.DEBUG else None
openapi_url = f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None

# --- GLOBAL ERROR RESPONSES ---
responses: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Bad Request"},
    401: {"model": ErrorResponse, "description": "Unauthorized"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
    404: {"model": ErrorResponse, "description": "Not Found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Validation Error"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"},
}

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    responses=responses,
)

# --- CORS SETUP ---
if settings.DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# --- EXCEPTION HANDLERS ---

# 1. Наши кастомные ошибки (бизнес-логика)
app.add_exception_handler(BaseAPIException, api_exception_handler)  # type: ignore


# 2. Глобальный перехватчик всех остальных ошибок (Last Resort)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Если DEBUG=True, позволяем FastAPI показать стандартную страницу с трейсбеком (удобно для разработки)
    if settings.DEBUG:
        raise exc

    # В проде логируем ошибку и отдаем нейтральный JSON
    logger.exception(f"🔥 Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred. Please try again later.",
            }
        },
    )


app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.PROJECT_NAME}


@app.get("/", tags=["System"])
async def root() -> dict[str, str]:
    if settings.DEBUG:
        return {"message": "Welcome to PinLite API. Go to /docs for Swagger."}
    return {"message": "Welcome to PinLite API."}
