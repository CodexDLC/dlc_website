# 📄 Router Discovery

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The `Router Discovery` system provides a centralized way to collect and assemble `aiogram.Router` instances from all installed features. This ensures that the bot's main dispatcher is automatically updated when new features are added.

## 🛠️ Functions

Located in: `src/telegram_bot/core/routers.py`

### `collect_feature_routers()`

Scans the features listed in `INSTALLED_FEATURES` for `aiogram` routers.

- **Process**:
    1. Iterates through each feature path in `INSTALLED_FEATURES`.
    2. Attempts to import the `handlers` module for that feature (e.g., `src.telegram_bot.features.bot_menu.handlers`).
    3. Looks for an attribute named `router` within that module.
    4. If a valid `Router` is found, it is added to the collection.
- **Returns**: A list of discovered `Router` instances.

### `build_main_router()`

Assembles the root router for the entire application.

- **Process**:
    1. Creates a new `main_router`.
    2. Calls `collect_feature_routers()` to get all feature-specific routers.
    3. Includes all discovered routers into the `main_router`.
    4. Includes the `common_fsm_router` (shared FSM handlers).
- **Returns**: The fully assembled `main_router`.

## 🧩 Integration

The `main_router` is typically included in the `Dispatcher` during the bot's startup:

```python
main_router = build_main_router()
dispatcher.include_router(main_router)
```

## 📝 Requirements for Features

For a feature's handlers to be automatically discovered, it must:
1.  Be listed in `INSTALLED_FEATURES` (in `core/settings.py`).
2.  Have a `handlers.py` (or `handlers/__init__.py`) file.
3.  Expose an `aiogram.Router` instance named `router` in that file.
