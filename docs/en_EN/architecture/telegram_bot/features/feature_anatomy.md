# 📜 Feature Anatomy

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

Every feature follows a standardized structure. This document describes the anatomy of a feature and the role of each file.

---

## 📁 Directory Structure

```text
features/{feature_name}/
├── feature_setting.py        # Feature manifest (States, GC, Menu, Factory)
├── menu.py                   # Menu button config (optional)
├── handlers/
│   ├── __init__.py           # Must export: router
│   └── handlers.py           # aiogram handlers (thin, no logic)
├── logic/
│   ├── __init__.py
│   ├── orchestrator.py       # Business logic coordinator
│   └── state_manager.py      # Draft storage (optional, for multi-step forms)
├── contracts/
│   ├── __init__.py
│   └── contract.py           # Protocol interface for data access
├── ui/
│   ├── __init__.py
│   └── ui.py                 # Pure rendering (data → ViewResultDTO)
├── resources/
│   ├── __init__.py
│   ├── texts.py              # Text constants
│   ├── callbacks.py          # CallbackData classes
│   ├── keyboards.py          # Keyboard builders
│   └── formatters.py         # Data formatters
└── services/                 # Feature-specific services (optional)
    └── ...
```

---

## 📋 feature_setting.py (Manifest)

This is the feature's declaration file. `FeatureDiscoveryService` reads it at startup.

```python
from aiogram.fsm.state import State, StatesGroup

# 1. States
class MyFeatureStates(StatesGroup):
    main = State()
    editing = State()

STATES = MyFeatureStates

# 2. Garbage Collector
GARBAGE_COLLECT = True          # Auto-register all STATES
# OR: GARBAGE_STATES = [MyFeatureStates.editing]  # Explicit list
# OR: GARBAGE_COLLECT = False   # Disabled

# 3. Menu Config (optional — only if feature appears in dashboard)
MENU_CONFIG = {
    "key": "my_feature",
    "text": "✨ My Feature",
    "description": "Short description for dashboard",
    "target_state": "my_feature",
    "priority": 50,             # Lower = higher in menu
    "is_admin": False,          # Requires owner role
    "is_superuser": False,      # Requires developer role
}

# 4. Factory (DI)
def create_orchestrator(container):
    # Choose data provider based on mode (API vs Direct)
    data_provider = container.some_client
    ui = MyFeatureUI()
    return MyFeatureOrchestrator(provider=data_provider, ui=ui)
```

---

## 🔄 Data Flow

```text
Telegram Update
  → Middleware (inject container)
    → Handler (thin routing layer)
      → Orchestrator (business logic)
        → Contract (data provider: API or DB)
        → UI (pure rendering)
      ← UnifiedViewDTO
    → ViewSender (send/edit messages)
  → Telegram API
```

---

## 📜 Contracts (Protocols)

Contracts define **what data** the orchestrator needs, not **how** to get it:

```python
class MyDataProvider(Protocol):
    async def get_items(self, user_id: int) -> list[Item]: ...
    async def create_item(self, data: ItemDTO) -> Item: ...
```

**API Mode:** Implemented by an HTTP client (calls FastAPI).
**Direct Mode:** Implemented by a repository (calls SQLAlchemy).

The orchestrator receives the contract via DI and does not know which mode is active.

---

## 🎨 UI Layer

Pure transformation functions. No side effects, no API calls:

```python
class MyFeatureUI:
    def render_main(self, items: list[Item]) -> ViewResultDTO:
        text = format_items(items)
        kb = build_items_keyboard(items)
        return ViewResultDTO(text=text, kb=kb)
```

---

## 🧩 Handler Pattern

Every handler follows the same structure:

```python
@router.callback_query(MyCallback.filter(F.action == "action"))
async def handle_action(call, callback_data, state, container):
    await call.answer()

    # 1. Get orchestrator from container
    orchestrator = container.features["my_feature"]

    # 2. Set up Director for navigation
    director = Director(container, state, call.from_user.id)
    orchestrator.set_director(director)

    # 3. Call business logic
    view_dto = await orchestrator.handle_action(callback_data)

    # 4. Send response
    state_data = await state.get_data()
    sender = ViewSender(call.bot, state, state_data, call.from_user.id)
    await sender.send(view_dto)
```

Handlers contain **zero business logic**. All decisions happen in the orchestrator.

---

## 🚀 Creating a New Feature

### Option 1: CLI Generator

```bash
python -m src.telegram_bot.manage create_feature my_feature
```

### Option 2: Manual

1. Copy the structure from an existing feature
2. Create `feature_setting.py` with States, GC, Menu, Factory
3. Create `handlers/__init__.py` that exports `router`
4. Add to `INSTALLED_FEATURES` in `settings.py`
