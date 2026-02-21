# 📜 Feature Setting

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the configuration and setup for the Redis Errors feature. It includes FSM states, garbage collection settings, and the factory function for creating the feature's orchestrator.

## 1. States Definition (`ErrorStates`)

```python
class ErrorStates(StatesGroup):
    main = State()
```
Defines the FSM states for the error handling feature. Currently, it includes a single `main` state.

*   `STATES`: Alias for `ErrorStates`.

## 2. Garbage Collector Settings (`GARBAGE_COLLECT`)

```python
GARBAGE_COLLECT = True
```
A boolean flag indicating whether messages received in the states defined by this feature should be considered "garbage" and potentially ignored or deleted. When `True`, the `GarbageStateRegistry` will register these states.

## 3. Menu Settings (`MENU_CONFIG`)

```python
# Ошибки НЕ должны быть в главном меню
# MENU_CONFIG = ...
```
This section is commented out, explicitly stating that error handling features should not appear in the main bot menu.

## 4. Factory (`create_orchestrator`)

```python
def create_orchestrator(container):
    return ErrorOrchestrator()
```
A factory function responsible for creating and returning an instance of `ErrorOrchestrator`. This function is used by the Dependency Injection (DI) container to instantiate the orchestrator for this feature.

*   `container`: The main `BotContainer` instance, which can be used to resolve other dependencies if needed (though not used directly in this example).
