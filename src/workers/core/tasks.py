from typing import Any

from loguru import logger as log


async def requeue_to_stream(ctx: dict[str, Any], stream_name: str, payload: dict[str, Any]) -> None:
    """
    Универсальная задача для возврата сообщения в Redis Stream.
    Используется Ботом для повторной обработки событий при сбоях.
    """
    sm = ctx.get("stream_manager")
    if not sm:
        log.error("requeue_to_stream | StreamManager not found in context")
        return

    # Увеличиваем счетчик попыток
    retries = int(payload.get("_retries", 0)) + 1
    if retries > 5:
        log.error(f"requeue_to_stream | Max retries reached for message type='{payload.get('type')}'. Dropping.")
        return

    payload["_retries"] = str(retries)

    try:
        await sm.add_event(stream_name, payload)
        log.info(f"requeue_to_stream | Message requeued to '{stream_name}' (retry #{retries})")
    except Exception as e:
        log.error(f"requeue_to_stream | Failed to add event to stream: {e}")


# Список базовых задач, которые должны быть в каждом воркере
CORE_FUNCTIONS = [
    requeue_to_stream,
]
