# 📄 Garbage Collector (FSM)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The `Garbage Collector` system is designed to keep the bot's chat clean by automatically identifying and deleting "garbage" messages (e.g., random text sent by a user when the bot expects only button clicks).

## 🏗️ Class: GarbageStateRegistry

Located in: `src/telegram_bot/core/garbage_collector.py`

This is a static registry that stores FSM states where incoming text messages are considered unwanted.

### Methods

#### `register(state)`
Registers a state or a group of states as "garbage-prone".
- Supports individual `State` objects.
- Supports `StatesGroup` classes (automatically registers all states in the group).
- Supports lists/tuples of states.

#### `is_garbage(state_name)`
Checks if a given state name is present in the registry.

---

## 🏗️ Class: IsGarbageStateFilter

An `aiogram.Filter` that uses the `GarbageStateRegistry` to determine if the current user's state is marked for garbage collection.

### Usage in Handlers

This filter is typically used in a global handler to catch and delete messages:

```python
@router.message(IsGarbageStateFilter())
async def handle_garbage_message(message: Message):
    await message.delete()
```

## 🧩 Integration

Features register their states during initialization (usually in `feature_setting.py` or via `FeatureDiscoveryService`):

```python
GarbageStateRegistry.register(MyFeatureStates.waiting_for_click)
```
