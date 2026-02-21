from typing import Any, Protocol


class MenuDiscoveryProvider(Protocol):
    """
    Контракт для получения списка кнопок меню.
    Реализуется сервисом FeatureDiscoveryService.
    """

    def get_menu_buttons(self, is_admin: bool | None = None) -> dict[str, dict[str, Any]]:
        """
        Возвращает кнопки меню с возможностью фильтрации по админ-статусу.
        """
        ...
