from collections.abc import Callable
from typing import Any


class RedisRouter:
    """
    Роутер для группировки хендлеров Redis Stream.
    Позволяет создавать модульные обработчики событий.
    """

    def __init__(self):
        # {message_type: [(handler_func, filter_func), ...]}
        # Хендлер принимает (payload, container)
        self._handlers: dict[
            str, list[tuple[Callable[[dict[str, Any], Any], Any], Callable[[dict[str, Any]], bool] | None]]
        ] = {}

    def message(self, message_type: str, filter_func: Callable[[dict[str, Any]], bool] | None = None):
        """
        Декоратор для регистрации хендлера на определенный тип сообщения.
        """

        def decorator(handler: Callable[[dict[str, Any], Any], Any]):
            if message_type not in self._handlers:
                self._handlers[message_type] = []
            self._handlers[message_type].append((handler, filter_func))
            return handler

        return decorator

    @property
    def handlers(self):
        """Возвращает зарегистрированные хендлеры."""
        return self._handlers
