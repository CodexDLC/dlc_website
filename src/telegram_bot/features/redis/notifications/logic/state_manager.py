from typing import Any, cast

from aiogram.fsm.context import FSMContext

from src.telegram_bot.services.fsm.base_manager import BaseStateManager


class DjangoListenerStateManager(BaseStateManager):
    """
    Менеджер состояния (Draft) для фичи DjangoListener.

    Используется для управления временными данными внутри фичи (фильтры, пагинация, формы).
    Наследуется от BaseStateManager, который обеспечивает изоляцию данных по ключу фичи.

    Примеры использования:
    - toggle_filter(filter_id): Включить/выключить фильтр
    - set_page(page): Переключить страницу
    - get_api_payload(): Собрать данные для отправки в API
    """

    def __init__(self, state: FSMContext):
        # feature_key обеспечивает уникальность данных в FSM
        super().__init__(state, feature_key="notifications")

    # --- Примеры реализации логики ---

    async def set_page(self, page: int) -> None:
        """Пример: Установка страницы пагинации."""
        await self.set_value("page", page)

    async def get_page(self) -> int:
        """Пример: Получение текущей страницы (по умолчанию 1)."""
        return cast("int", await self.get_value("page", default=1))

    async def toggle_option(self, option_id: str) -> dict[str, Any]:
        """
        Пример: Логика переключателя (Toggle).
        Если опция уже выбрана - убираем, иначе - ставим.
        """
        current_data = await self.get_payload()
        current_option = current_data.get("selected_option")

        new_option = None if current_option == option_id else option_id

        return await self.update(selected_option=new_option)
