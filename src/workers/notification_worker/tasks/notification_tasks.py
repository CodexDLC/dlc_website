from typing import TYPE_CHECKING, Any, cast

from loguru import logger as log

from src.shared.core.constants import RedisStreams

if TYPE_CHECKING:
    from src.shared.core.manager_redis.manager import StreamManager


async def send_domain_event_task(ctx: dict[str, Any], event_data: dict[str, Any], admin_id: int | None = None) -> None:
    """
    Пример задачи: отправка доменного события в Redis Stream (для Telegram Bot).

    Используется когда Backend хочет уведомить Bot о каком-либо событии.
    Bot слушает стрим RedisStreams.BotEvents.NAME и обрабатывает события.

    TODO: Переименуй функцию и замени "example_event" на тип события своего домена.
    TODO: Обнови task_aggregator.py если переименовал функцию.
    """
    log.info(f"Task: send_domain_event_task | id={event_data.get('id')}")

    # Use cast to satisfy Mypy
    stream_manager = cast("StreamManager", ctx.get("stream_manager"))
    if not stream_manager:
        log.error("StreamManager not found in context. Cannot send event.")
        return

    event_payload = event_data.copy()
    # TODO: Replace "example_event" with your domain event type
    event_payload["type"] = "example_event"

    try:
        stream_name = RedisStreams.BotEvents.NAME
        message_id = await stream_manager.add_event(stream_name, event_payload)

        if message_id:
            log.info(f"Event sent to stream '{stream_name}' | msg_id={message_id}")
        else:
            log.error(f"Failed to send event to stream '{stream_name}'")

    except Exception as e:
        log.exception(f"Error sending domain event task: {e}")


async def requeue_event_task(ctx: dict[str, Any], event_data: dict[str, Any]) -> None:
    """
    Универсальная задача для возврата события в Redis Stream (Retry mechanism).
    Используется при сбоях обработки — возвращает событие в очередь для повторной попытки.
    Максимум 5 попыток (счётчик _retries в payload).
    """
    log.info(f"Task: requeue_event_task | type={event_data.get('type')}")

    stream_manager = cast("StreamManager", ctx.get("stream_manager"))
    if not stream_manager:
        log.error("StreamManager not found in context.")
        return

    try:
        stream_name = RedisStreams.BotEvents.NAME
        # Увеличиваем счетчик попыток
        retries = int(event_data.get("_retries", 0)) + 1
        event_data["_retries"] = str(retries)

        message_id = await stream_manager.add_event(stream_name, event_data)
        log.info(f"Event requeued to '{stream_name}' | retry={retries} | msg_id={message_id}")

    except Exception as e:
        log.error(f"Failed to requeue event: {e}")
