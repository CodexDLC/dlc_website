from typing import Any
from loguru import logger as log
from src.telegram_bot.services.redis.router import RedisRouter

# Роутер для событий из Redis Stream
redis_router = RedisRouter()

@redis_router.message("your_event_type")
async def handle_{feature_key}_event(message_data: dict[str, Any], container: Any):
    """
    Хендлер для событий {class_name}.
    """
    try:
        # Оркестратор доступен как атрибут контейнера с префиксом redis_
        orchestrator = container.{container_key}
        view_sender = container.view_sender

        log.info(f"{class_name} | Processing event")

        # Логика обработки...
        # view_dto = orchestrator.handle_event(message_data)
        # await view_sender.send(view_dto)

    except Exception as e:
        log.exception(f"{class_name} | Failed to process event: {{e}}")
