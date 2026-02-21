from typing import Any

from ...schemas.site_settings import SiteSettingsSchema
from ..config import CommonSettings
from ..redis_service import RedisService


class SiteSettingsManager:
    """
    Менеджер для получения глобальных настроек сайта из Redis.
    Используется Ботом и Воркером.
    """

    def __init__(self, redis_service: RedisService, settings: CommonSettings):
        self.redis = redis_service
        self.key = settings.redis_site_settings_key

    async def get_settings(self) -> dict[str, Any]:
        """
        Получает все настройки сайта и конвертирует типы.
        """
        data = await self.redis.get_all_hash(self.key)
        if not data:
            return {}

        return self._parse_settings(data)

    async def get_settings_obj(self) -> SiteSettingsSchema:
        """
        Получает настройки сайта и возвращает объект Pydantic-схемы.
        """
        data = await self.get_settings()
        return SiteSettingsSchema(**data)

    async def get_field(self, field_name: str) -> Any:
        """
        Получает конкретное поле настроек.
        """
        value = await self.redis.get_hash_field(self.key, field_name)
        if value is None:
            return None

        # Парсим одиночное значение через тот же механизм
        parsed = self._parse_settings({field_name: value})
        return parsed.get(field_name)

    def _parse_settings(self, data: dict[str, str]) -> dict[str, Any]:
        """
        Преобразует строковые значения из Redis в Python-типы.
        """
        result: dict[str, Any] = {}
        for k, v in data.items():
            # Логические значения
            if v.lower() in ("true", "false"):
                result[k] = v.lower() == "true"
            else:
                result[k] = v
        return result
