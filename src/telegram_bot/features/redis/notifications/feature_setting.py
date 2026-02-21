from aiogram.fsm.state import State, StatesGroup


# 1. Определение состояний
class NotificationsStates(StatesGroup):
    main = State()


STATES = NotificationsStates

# 2. Настройки Garbage Collector
GARBAGE_COLLECT = True

# 3. Настройки Меню (Закомментировано, так как фича не интерактивна)
# MENU_CONFIG = {
#     "key": "notifications",
#     "text": "🔔 Уведомления",
#     "icon": "🔔",
#     "description": "Системные уведомления",
#     "target_state": "notifications",
#     "priority": 50,
#     # Права доступа
#     "is_admin": True,      # Только для владельцев (Owner)
#     "is_superuser": False,  # Только для разработчиков (Superuser)
# }


# 4. Фабрика (DI)
def create_orchestrator(container):
    from .logic.orchestrator import NotificationsOrchestrator

    # Передаем настройки бота в оркестратор
    return NotificationsOrchestrator(settings=container.settings)
