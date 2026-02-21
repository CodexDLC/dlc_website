from typing import Any

from loguru import logger as log

from src.telegram_bot.core.container import BotContainer
from src.telegram_bot.services.redis.router import RedisRouter

# Роутер для событий из Redis Stream
redis_router = RedisRouter()


@redis_router.message("system_error")
async def handle_system_error_notification(message_data: dict[str, Any], container: BotContainer):
    """
    Хендлер для системных ошибок.
    """
    try:
        orchestrator = container.features.get("redis_errors")
        if not orchestrator:
            return

        log.info("Errors | Processing 'system_error' event")

        # 1. Оркестратор обрабатывает данные
        view_dto = orchestrator.handle_error(message_data)

        # 2. Отправляем через централизованный сендер
        if container.view_sender:
            await container.view_sender.send(view_dto)

    except Exception as e:
        log.exception(f"Errors | Failed to process error notification: {e}")
