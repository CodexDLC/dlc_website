# 📜 Feature Setting

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the configuration and setup for the Redis Notifications feature. It includes FSM states, garbage collection settings, and the factory function for creating the feature's orchestrator.

## 1. States Definition (`NotificationsStates`)

```python
class NotificationsStates(StatesGroup):
    main = State()
```
Defines the FSM states for the notifications feature. Currently, it includes a single `main` state.

*   `STATES`: Alias for `NotificationsStates`.

## 2. Garbage Collector Settings (`GARBAGE_COLLECT`)

```python
GARBAGE_COLLECT = True
```
A boolean flag indicating whether messages received in the states defined by this feature should be considered "garbage" and potentially ignored or deleted. When `True`, the `GarbageStateRegistry` will register these states.

## 3. Menu Settings (`MENU_CONFIG`)

```python
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
```
This section is commented out, indicating that this feature is not intended to be part of the main bot menu as it's likely a non-interactive, background processing feature.

## 4. Factory (`create_orchestrator`)

```python
def create_orchestrator(container):
    from .logic.orchestrator import NotificationsOrchestrator
    return NotificationsOrchestrator(settings=container.settings)
```
A factory function responsible for creating and returning an instance of `NotificationsOrchestrator`. This function is used by the Dependency Injection (DI) container to instantiate the orchestrator for this feature.

*   `container`: The main `BotContainer` instance, which provides access to application settings and other dependencies. The `BotSettings` are passed to the `NotificationsOrchestrator`.
