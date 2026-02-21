from typing import Any, TypeVar, cast

from aiogram.fsm.context import FSMContext

T = TypeVar("T")


class BaseStateManager:
    """
    Базовый менеджер состояния (Draft Manager).
    Обеспечивает изоляцию данных фичи внутри FSM.
    """

    def __init__(self, state: FSMContext, feature_key: str):
        self.state = state
        # Уникальный ключ для хранения данных этой фичи
        self.storage_key = f"draft:{feature_key}"

    async def get_payload(self) -> dict[str, Any]:
        """Возвращает все данные черновика."""
        data = await self.state.get_data()
        return cast("dict[str, Any]", data.get(self.storage_key, {}))

    async def update(self, **kwargs: Any) -> dict[str, Any]:
        """
        Обновляет черновик переданными полями.
        Возвращает обновленный словарь.
        """
        current = await self.get_payload()
        current.update(kwargs)

        await self.state.update_data({self.storage_key: current})
        return current

    async def clear(self) -> None:
        """Очищает черновик."""
        await self.state.update_data({self.storage_key: {}})

    async def set_value(self, key: str, value: Any) -> None:
        """Устанавливает конкретное значение."""
        await self.update(**{key: value})

    async def get_value(self, key: str, default: Any = None) -> Any:
        """Получает конкретное значение."""
        payload = await self.get_payload()
        return payload.get(key, default)
