from aiogram.fsm.state import State, StatesGroup

from src.telegram_bot.features.telegram.commands.contracts.commands_contract import AuthDataProvider
from src.telegram_bot.features.telegram.commands.logic.orchestrator import StartOrchestrator
from src.telegram_bot.features.telegram.commands.ui.commands_ui import CommandsUI


# 1. Определение состояний
class CommandsStates(StatesGroup):
    main = State()


STATES = CommandsStates

# 2. Настройки Garbage Collector
GARBAGE_COLLECT = False

# 3. Настройки Меню
# Фича commands является точкой входа (/start), поэтому она не должна отображаться в самом меню.
MENU_CONFIG = None


# Временная заглушка для AuthDataProvider
class MockAuthDataProvider(AuthDataProvider):
    async def upsert_user(self, user_dto):
        # Просто ничего не делаем, пока нет реального API
        pass

    async def logout(self, user_id: int):
        # Заглушка для метода logout
        pass


# 4. Фабрика (DI)
def create_orchestrator(container):
    """
    Создает оркестратор.
    """
    # Используем заглушку, так как auth_client удален из контейнера
    data_provider = MockAuthDataProvider()

    ui = CommandsUI()

    return StartOrchestrator(auth_provider=data_provider, ui=ui, settings=container.settings)
