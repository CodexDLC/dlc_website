# 📜 Director

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `Director` class, which acts as the central coordinator for navigation and scene transitions between different features (orchestrators) within the Telegram bot. It manages FSM states and delegates rendering tasks to the appropriate orchestrators.

## `Director` Class

The `Director` is a crucial service for orchestrating the user's journey through the bot. It ensures that when a user moves from one feature to another, the correct orchestrator is activated and initialized with the necessary data.

### Initialization (`__init__`)

```python
def __init__(self, container: "BotContainer", state: FSMContext | None = None, user_id: int | None = None):
```
Initializes the `Director` service.

*   `container` (`BotContainer`): The main Dependency Injection container, providing access to all feature orchestrators.
*   `state` (`FSMContext | None`): The Aiogram FSM context for the current user. This is optional, as the Director might be initialized in contexts without an active FSM state.
*   `user_id` (`int | None`): The ID of the current user. This is also optional.

### `set_scene` Method

```python
async def set_scene(self, feature: str, payload: Any) -> Any:
```
This asynchronous method orchestrates inter-feature transitions. It changes the FSM state (if applicable) and calls the entry logic of the target feature's orchestrator.

*   `feature` (`str`): The key of the target feature (as registered in `container.features`).
*   `payload` (`Any`): Data to initialize the target feature. If `None`, the orchestrator's `handle_entry` will be called without specific payload.

**Process:**
1.  **Retrieve Orchestrator:** Fetches the orchestrator instance for the specified `feature` from `container.features`. If the feature is not found, it logs an error and returns `None`.
2.  **Set Director:** If the orchestrator implements `set_director`, the `Director` instance itself is passed to the orchestrator, allowing the orchestrator to interact with the `Director` for further navigation.
3.  **Entry Logic:** Calls the `handle_entry` method of the target orchestrator with the `user_id` and `payload`. This method is responsible for initializing the feature and preparing its UI.
4.  **Fallback:** Provides a fallback to `orchestrator.render()` for older orchestrators that might not implement `handle_entry`.

**Returns:**
`Any`: The result of the orchestrator's `handle_entry` or `render` method, typically a `UnifiedViewDTO`.

### `render` Method (Legacy)

```python
async def render(self, feature: str, service: str, payload: Any) -> Any:
```
This method is marked as a legacy method for intra-feature transitions. It currently delegates to `set_scene()`. It's recommended to use `set_scene()` or direct orchestrator methods for transitions.

### `OrchestratorProtocol`

```python
@runtime_checkable
class OrchestratorProtocol(Protocol):
    async def render(self, payload: Any) -> Any: ...
    async def handle_entry(self, user_id: int | None, payload: Any = None) -> Any: ...
    def set_director(self, director: Any): ...
```
A `Protocol` defining the expected interface for any orchestrator that interacts with the `Director`. This ensures type safety and consistency across orchestrator implementations.

*   `render`: Method for rendering data.
*   `handle_entry`: Method for handling the entry point of a feature.
*   `set_director`: Method for setting the `Director` instance.
