from typing import Any

from ..redis_service import RedisService


class StreamManager:
    """
    Менеджер для работы с Redis Streams.
    Использует публичные методы RedisService.
    """

    def __init__(self, redis_service: RedisService):
        self.redis = redis_service

    async def add_event(self, stream_name: str, data: dict[str, Any]) -> str | None:
        """Добавляет событие в стрим."""
        return await self.redis.stream_add(stream_name, data)

    async def create_group(self, stream_name: str, group_name: str) -> None:
        """Создает группу потребителей (если не существует)."""
        await self.redis.stream_create_group(stream_name, group_name)

    async def read_events(self, stream_name: str, group_name: str, consumer_name: str, count: int = 10) -> list[tuple]:
        """Читает новые события."""
        return await self.redis.stream_read_group(stream_name, group_name, consumer_name, count)

    async def ack_event(self, stream_name: str, group_name: str, event_id: str) -> None:
        """Подтверждает обработку события."""
        await self.redis.stream_ack(stream_name, group_name, event_id)
