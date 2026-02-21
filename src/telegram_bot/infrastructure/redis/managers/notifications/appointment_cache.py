import json
from typing import Any

from src.shared.core.redis_service import RedisService

from .notification_keys import NotificationKeys


class EventCacheManager:
    """
    Generic Redis cache manager for temporary storage of event notification data.
    TODO: Rename and extend for your domain entity if needed.
    """

    def __init__(self, redis_service: RedisService, ttl: int = 86400):
        self.redis = redis_service
        self.ttl = ttl

    def _get_key(self, entity_id: int | str) -> str:
        return NotificationKeys.get_cache_key(entity_id)

    async def save(self, entity_id: int | str, data: dict[str, Any]) -> None:
        """Saves entity data as JSON to Redis cache."""
        key = self._get_key(entity_id)
        await self.redis.set_value(key, json.dumps(data, ensure_ascii=False), ttl=self.ttl)

    async def get(self, entity_id: int | str) -> dict[str, Any] | None:
        """Retrieves entity data from Redis cache."""
        key = self._get_key(entity_id)
        data = await self.redis.get_value(key)
        if data:
            return json.loads(data)
        return None

    async def delete(self, entity_id: int | str) -> None:
        """Removes entity data from cache."""
        key = self._get_key(entity_id)
        await self.redis.delete_key(key)


# Backward-compatible alias
AppointmentCacheManager = EventCacheManager
