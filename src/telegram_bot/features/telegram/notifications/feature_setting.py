from aiogram.fsm.state import State, StatesGroup


class NotificationsStates(StatesGroup):
    main = State()


STATES = NotificationsStates
GARBAGE_COLLECT = True

MENU_CONFIG = {
    "key": "notifications",
    "text": "✨ Notifications",
    "icon": "✨",
    "description": "Управление уведомлениями",
    "target_state": "notifications",
    "priority": 50,
    "is_admin": True,
    "is_superuser": False,
}


def create_orchestrator(container):
    from src.telegram_bot.core.api_client import BaseApiClient
    from src.telegram_bot.infrastructure.api_route.notifications import NotificationsApiProvider

    from .logic.orchestrator import NotificationsOrchestrator

    django_api = BaseApiClient(
        base_url=container.settings.backend_api_url, api_key=container.settings.backend_api_key, timeout=10.0
    )

    data_provider = NotificationsApiProvider(api_client=django_api)

    # Передаем container напрямую в конструктор
    return NotificationsOrchestrator(container=container, django_api=django_api, data_provider=data_provider)
