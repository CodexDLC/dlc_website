# 📜 Service

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `FeatureDiscoveryService` class, which is responsible for dynamically discovering and registering various configurations and components of features within the Telegram bot application. It supports both UI-oriented (Telegram) and background (Redis) features, promoting a modular and extensible architecture.

## `FeatureDiscoveryService` Class

The `FeatureDiscoveryService` automates the process of integrating new features into the bot by scanning predefined paths for `feature_setting.py` files and extracting relevant configurations, such as menu buttons, FSM states for garbage collection, and Redis Stream handlers.

### Initialization (`__init__`)

```python
def __init__(self) -> None:
```
Initializes the `FeatureDiscoveryService`.

**Key Action:**
*   Initializes `self._loaded_features` as an empty set, which can be used to track successfully loaded features (though not explicitly used for that purpose in the current methods).

### `discover_all` Method

```python
def discover_all(self) -> None:
```
Executes a full discovery cycle, scanning all features listed in `INSTALLED_FEATURES` and `INSTALLED_REDIS_FEATURES` for their respective configurations.

**Process:**
1.  Iterates through `INSTALLED_FEATURES`:
    *   Calls `_discover_menu()` to find and process menu configurations.
    *   Calls `_discover_garbage_states()` to register FSM states for garbage collection.
2.  Iterates through `INSTALLED_REDIS_FEATURES`:
    *   Calls `_discover_redis_handlers()` to include Redis Stream routers.
    *   Calls `_discover_garbage_states()` to register FSM states for garbage collection.

### `create_feature_orchestrators` Method

```python
def create_feature_orchestrators(self, container: "BotContainer") -> dict[str, Any]:
```
Creates and returns a dictionary of orchestrator instances for all discovered features. It handles naming conventions for Redis-based features.

*   `container` (`BotContainer`): The main Dependency Injection container, which is passed to the orchestrator factories.

**Process:**
1.  Iterates through both `INSTALLED_FEATURES` and `INSTALLED_REDIS_FEATURES`.
2.  For each feature, it loads its `feature_setting` module using `_load_feature_setting()`.
3.  If a `create_orchestrator` factory function is found in the module, it calls this factory, passing the `container`.
4.  Constructs a unique key for the orchestrator (e.g., `notifications` or `redis_notifications`) and stores the created instance in the `orchestrators` dictionary.
5.  Logs the creation or any errors during the orchestrator instantiation.

**Returns:**
`dict[str, Any]`: A dictionary where keys are feature names (with `redis_` prefix for Redis features) and values are the instantiated orchestrator objects.

### `get_menu_buttons` Method

```python
def get_menu_buttons(self) -> dict[str, dict[str, Any]]:
```
Collects and returns a dictionary of menu button configurations from all UI-oriented features.

**Process:**
1.  Iterates through `INSTALLED_FEATURES`.
2.  For each feature, it calls `_discover_menu()` to retrieve its menu configuration.
3.  If a menu configuration is found, it extracts the button's key and adds the configuration to the `buttons` dictionary.

**Returns:**
`dict[str, dict[str, Any]]`: A dictionary where keys are button keys and values are their configuration dictionaries.

### Private Helper Methods

#### `_load_feature_setting` Method

```python
def _load_feature_setting(self, feature_path: str) -> Any | None:
```
Attempts to dynamically import the `feature_setting.py` module for a given `feature_path`.

*   `feature_path` (`str`): The dot-separated path to the feature (e.g., `features.telegram.commands`).

**Process:**
*   Tries to import `src.telegram_bot.{feature_path}.feature_setting` or `src.telegram_bot.{feature_path}`.
*   Handles `ImportError` gracefully.

**Returns:**
`Any | None`: The imported module object if successful, otherwise `None`.

#### `_discover_menu` Method

```python
def _discover_menu(self, feature_path: str) -> dict[str, Any] | None:
```
Discovers and returns the `MENU_CONFIG` dictionary from a feature's `menu.py` module.

*   `feature_path` (`str`): The dot-separated path to the feature.

**Process:**
*   Tries to import `src.telegram_bot.{feature_path}.menu`.
*   If the module contains a `MENU_CONFIG` dictionary, it is returned.

**Returns:**
`dict[str, Any] | None`: The menu configuration dictionary if found, otherwise `None`.

#### `_discover_garbage_states` Method

```python
def _discover_garbage_states(self, feature_path: str) -> None:
```
Discovers and registers FSM states from a feature's `feature_setting.py` module with the `GarbageStateRegistry`.

*   `feature_path` (`str`): The dot-separated path to the feature.

**Process:**
1.  Loads the feature's `feature_setting` module.
2.  Checks for `GARBAGE_STATES` or `GARBAGE_COLLECT` flags.
3.  If found, it registers the specified states (or all `STATES` if `GARBAGE_COLLECT` is `True`) with `GarbageStateRegistry.register()`.

#### `_discover_redis_handlers` Method

```python
def _discover_redis_handlers(self, feature_path: str) -> None:
```
Discovers and includes `RedisRouter` instances from a feature's `handlers.py` module into the `bot_redis_dispatcher`.

*   `feature_path` (`str`): The dot-separated path to the feature.

**Process:**
1.  Tries to import `src.telegram_bot.{feature_path}.handlers`.
2.  If the module contains a `redis_router` instance of type `RedisRouter`, it includes this router into the global `bot_redis_dispatcher`.
3.  Logs the connection or any errors during the process.
