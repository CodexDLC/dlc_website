# 📜 Container

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `ContainerMiddleware`, an Aiogram middleware responsible for injecting the `BotContainer` instance into the data dictionary of incoming updates. This allows handlers to easily access all application services and dependencies managed by the container.

## `ContainerMiddleware` Class

The `ContainerMiddleware` facilitates Dependency Injection (DI) by making the central `BotContainer` available to any handler that processes an update.

### Initialization (`__init__`)

```python
def __init__(self, container: BotContainer):
```
Initializes the `ContainerMiddleware` with an instance of `BotContainer`.

*   `container` (`BotContainer`): The main Dependency Injection container of the bot application.

### `__call__` Method

```python
async def __call__(
    self,
    handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
    event: TelegramObject,
    data: dict[str, Any],
) -> Any:
```
This asynchronous method is the entry point for the middleware. It intercepts incoming `TelegramObject` events before they are processed by the main handlers.

*   `handler` (`Callable`): The next handler in the middleware chain or the final message handler.
*   `event` (`TelegramObject`): The incoming Telegram event object.
*   `data` (`dict[str, Any]`): A dictionary containing various data passed through the middleware chain.

**Process:**
1.  **Inject Container:** The `self.container` instance (which holds all application services and clients) is added to the `data` dictionary under the key `"container"`.
2.  **Pass to Next Handler:** The event and the augmented `data` dictionary are then passed to the `handler` for further processing.

**Returns:**
`Any`: The result of the `handler` after the `BotContainer` has been injected into the `data` dictionary.
