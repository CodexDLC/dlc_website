from aiogram.fsm.state import State, StatesGroup

from src.telegram_bot.features.redis.errors.logic.orchestrator import ErrorOrchestrator


# 1. Определение состояний
class ErrorStates(StatesGroup):
    main = State()


STATES = ErrorStates

# 2. Настройки Garbage Collector
GARBAGE_COLLECT = True

# 3. Настройки Меню
# Ошибки НЕ должны быть в главном меню
# MENU_CONFIG = ...


# 4. Фабрика (DI)
def create_orchestrator(container):
    return ErrorOrchestrator()
