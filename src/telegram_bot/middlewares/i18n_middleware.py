from typing import Any

from aiogram.types import User
from aiogram_i18n.managers import BaseManager
from loguru import logger as log


class FSMContextI18nManager(BaseManager):
    """
    Менеджер языка, который хранит выбор пользователя в FSM (Redis).
    """

    async def get_locale(self, event_from_user: User | None = None, **kwargs: Any) -> str:
        """
        Определяет язык.
        """
        user_id = event_from_user.id if event_from_user else "unknown"

        # 1. Пытаемся достать из стейта
        state = kwargs.get("state")
        if state:
            data = await state.get_data()
            if "locale" in data:
                locale = data["locale"]
                log.debug(f"I18nManager | user={user_id} source=FSM locale='{locale}'")
                return locale

        # 2. Берем из Telegram
        if event_from_user and event_from_user.language_code in ["ru", "de"]:
            locale = event_from_user.language_code
            log.debug(f"I18nManager | user={user_id} source=Telegram locale='{locale}'")
            return locale

        # 3. Дефолт
        log.debug(f"I18nManager | user={user_id} source=Default locale='de'")
        return "de"

    async def set_locale(self, locale: str, **kwargs: Any) -> None:
        """
        Сохраняет выбранный язык в FSM.
        """
        state = kwargs.get("state")
        if state:
            await state.update_data(locale=locale)
            log.info(f"I18nManager | Locale updated to '{locale}'")
