from typing import Protocol, Any

class {class_name}DataProvider(Protocol):
    """
    Контракт для доступа к данным фичи {class_name}.
    Реализация (Client или Repository) подставляется через DI.
    """

    async def get_data(self, user_id: int) -> Any:
        """Пример метода получения данных."""
        ...
