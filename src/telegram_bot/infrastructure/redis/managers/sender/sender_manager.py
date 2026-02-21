from src.shared.core.redis_service import RedisService

from .sender_key import SenderKeys


class SenderManager:
    """
    Менеджер для управления состоянием Sender (координаты UI).
    Хранит ID сообщений (menu_msg_id, content_msg_id) в Redis.
    """

    def __init__(self, redis_service: RedisService):
        self.redis = redis_service

    async def get_coords(self, session_key: int | str, is_channel: bool = False) -> dict[str, int]:
        """
        Получает координаты UI (ID сообщений).

        Args:
            session_key: user_id (int) или session_id (str).
            is_channel: Флаг, указывающий на тип ключа (User vs Channel).

        Returns:
            dict: Словарь с координатами, например {"menu_msg_id": 123, "content_msg_id": 124}.
                  Пустой словарь, если данных нет.
        """
        key = self._get_key(session_key, is_channel)

        # Используем get_all_hash, так как храним поля как HASH
        data = await self.redis.get_all_hash(key)

        if not data:
            return {}

        # Конвертируем значения в int, так как Redis возвращает строки
        coords = {}
        for k, v in data.items():
            try:
                coords[k] = int(v)
            except (ValueError, TypeError):
                continue

        return coords

    async def update_coords(self, session_key: int | str, coords: dict[str, int], is_channel: bool = False) -> None:
        """
        Обновляет координаты UI.

        Args:
            session_key: user_id или session_id.
            coords: Словарь с новыми координатами (частичное обновление).
            is_channel: Тип ключа.
        """
        if not coords:
            return

        key = self._get_key(session_key, is_channel)

        # Конвертируем в строки для Redis (хотя redis-py умеет сам, но для надежности)
        data_to_save = {k: str(v) for k, v in coords.items()}

        await self.redis.set_hash_fields(key, data_to_save)

    async def clear_coords(self, session_key: int | str, is_channel: bool = False) -> None:
        """
        Удаляет координаты UI (сброс состояния).
        """
        key = self._get_key(session_key, is_channel)
        await self.redis.delete_key(key)

    def _get_key(self, session_key: int | str, is_channel: bool) -> str:
        """
        Выбирает правильный ключ в зависимости от типа сессии.
        """
        if is_channel:
            return SenderKeys.get_channel_coords_key(str(session_key))
        return SenderKeys.get_user_coords_key(session_key)
