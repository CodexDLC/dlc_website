from typing import TYPE_CHECKING, Any

from aiogram import Bot
from loguru import logger as log

from .router import RedisRouter

if TYPE_CHECKING:
    from collections.abc import Callable


class BotRedisDispatcher:
    """
    Диспетчер для сообщений из Redis Stream, работающий по принципу aiogram.
    Позволяет регистрировать хендлеры с помощью декораторов и подключать роутеры.
    """

    def __init__(self, bot: Bot | None = None):
        self._bot = bot
        self._container = None  # Ссылка на BotContainer
        # Словарь для хранения зарегистрированных хендлеров
        self._handlers: dict[
            str, list[tuple[Callable[[dict[str, Any], Any], Any], Callable[[dict[str, Any]], bool] | None]]
        ] = {}
        log.info("BotRedisDispatcher initialized.")

    def set_bot(self, bot: Bot):
        self._bot = bot
        log.debug("Bot object set in BotRedisDispatcher.")

    def set_container(self, container):
        self._container = container
        log.debug("Container set in BotRedisDispatcher.")

    def include_router(self, router: RedisRouter):
        for message_type, handlers in router.handlers.items():
            if message_type not in self._handlers:
                self._handlers[message_type] = []
            self._handlers[message_type].extend(handlers)
        log.info(f"Included router with handlers for types: {list(router.handlers.keys())}")

    def on_message(self, message_type: str, filter_func: "Callable[[dict[str, Any]], bool] | None" = None):
        """
        Декоратор для регистрации хендлеров сообщений из Redis Stream.
        """

        def decorator(handler: "Callable[[dict[str, Any], Any], Any]"):
            if message_type not in self._handlers:
                self._handlers[message_type] = []
            self._handlers[message_type].append((handler, filter_func))
            log.debug(f"Registered handler for message_type='{message_type}' (handler: {handler.__name__})")
            return handler

        return decorator

    async def process_message(self, message_data: dict[str, Any]):
        """
        Обрабатывает входящее сообщение из Redis Stream.
        При ошибке в хендлере ставит задачу на повторную очередь через ARQ.
        """
        if not self._bot or not self._container:
            log.error("Bot or Container not set in BotRedisDispatcher.")
            return

        msg_type = message_data.get("type")
        if not msg_type:
            log.warning(f"Received Redis Stream message without 'type' field: {message_data}")
            return

        handlers_for_type = self._handlers.get(msg_type, [])
        if not handlers_for_type:
            log.debug(f"No handlers registered for message_type='{msg_type}'")
            return

        for handler, filter_func in handlers_for_type:
            try:
                if filter_func is None or filter_func(message_data):
                    log.debug(f"Calling handler {handler.__name__} for message_type='{msg_type}'")
                    await handler(message_data, self._container)
            except Exception as e:
                log.error(f"Error in Redis Stream handler {handler.__name__}: {e}")

                # Механизм Retry через ARQ
                if self._container.arq_pool:
                    try:
                        # Ставим задачу на перепостановку в стрим через 60 секунд
                        await self._container.arq_pool.enqueue_job(
                            "requeue_to_stream", stream_name="bot_events", payload=message_data, _defer_by=60
                        )
                        log.info(f"Retry scheduled for message_type='{msg_type}' via ARQ")
                    except Exception as arq_err:
                        log.error(f"Failed to schedule retry in ARQ: {arq_err}")

                raise e


# Глобальный экземпляр диспетчера
bot_redis_dispatcher = BotRedisDispatcher()
