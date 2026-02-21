from aiogram.fsm.state import State, StatesGroup

# 1. Определение состояний
class {class_name}States(StatesGroup):
    main = State()

STATES = {class_name}States

# 2. Настройки Garbage Collector
GARBAGE_COLLECT = True

# 3. Настройки Меню
MENU_CONFIG = {{
    "key": "{feature_key}",
    "text": "✨ {class_name}",
    "icon": "✨",
    "description": "Описание фичи {class_name}",
    "target_state": "{feature_key}",
    "priority": 50,
    # Права доступа
    "is_admin": False,      # Только для владельцев (Owner)
    "is_superuser": False,  # Только для разработчиков (Superuser)
}}

# 4. Фабрика (DI)
# def create_orchestrator(container):
#     from .logic.orchestrator import {class_name}Orchestrator
#     return {class_name}Orchestrator()
