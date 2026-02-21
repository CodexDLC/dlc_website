from aiogram.fsm.state import State, StatesGroup


# 1. Определение состояний
class BotMenuStates(StatesGroup):
    main = State()


STATES = BotMenuStates

# 2. Настройки Garbage Collector
GARBAGE_COLLECT = True

# 3. Настройки Меню
# bot_menu — это само меню, поэтому MENU_CONFIG не нужен
# MENU_CONFIG = ...

# 4. Фабрика (DI)
# bot_menu создаётся вручную в container, т.к. зависит от FeatureDiscoveryService.
# create_orchestrator здесь НЕ определён — container создаёт BotMenuOrchestrator напрямую.
