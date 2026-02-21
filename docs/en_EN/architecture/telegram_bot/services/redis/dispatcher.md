# 📜 Dispatcher

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `BotRedisDispatcher` class, which acts as a central dispatcher for messages received from Redis Streams. It operates similarly to Aiogram's dispatcher, allowing for the registration of handlers and the inclusion of `RedisRouter` instances to process various types of Redis Stream events.

## `BotRedisDispatcher` Class

The `BotRedisDispatcher` is responsible for routing incoming Redis Stream messages to the appropriate registered handlers, providing a flexible and extensible event processing mechanism.

### Initialization (`__init__`)

```python
def __init__(self, bot: Bot | None = None):
```
Initializes the `BotRedisDispatcher`.

*   `bot` (`Bot | None`): An optional `aiogram.Bot` instance. It can be set later using `set_bot()`.

**Key Actions:**
*   Initializes `self._bot` and `self._container` to `None`.
*   Initializes `self._handlers` as an empty dictionary, which will store registered handlers.

### `set_bot` Method

```python
def set_bot(self, bot: Bot):
```
Sets the `aiogram.Bot` object for the dispatcher. This is typically called after the bot instance has been created.

*   `bot` (`Bot`): The `aiogram.Bot` instance.

### `set_container` Method

```python
def set_container(self, container):
```
Sets the main Dependency Injection container (`BotContainer`) for the dispatcher. This allows handlers to access application services.

*   `container`: The `BotContainer` instance.

### `include_router` Method

```python
def include_router(self, router: RedisRouter):
```
Includes a `RedisRouter` into the dispatcher. All handlers registered within the provided `RedisRouter` are copied into the dispatcher's internal handler registry.

*   `router` (`RedisRouter`): An instance of `RedisRouter` containing handlers to be included.

### `on_message` Method (Decorator)

```python
def on_message(self, message_type: str, filter_func: Callable[[dict[str, Any]], bool] | None = None):
```
This method acts as a decorator for registering handlers for specific Redis Stream message types.

*   `message_type` (`str`): The type of message this handler should process.
*   `filter_func` (`Callable[[dict[str, Any]], bool] | None`): An optional filter function that must return `True` for the handler to be executed.

**Usage:**
```python
@dispatcher.on_message("my_event_type")
async def my_handler(payload: dict[str, Any], container: Any):
    # ... process event ...
```

**Returns:**
A decorator function that registers the decorated handler.

### `process_message` Method

```python
async def process_message(self, message_data: dict[str, Any]):
```
This asynchronous method is the core of the dispatcher. It processes an incoming message from a Redis Stream, identifies its type, and dispatches it to all matching registered handlers.

*   `message_data` (`dict[str, Any]`): The raw dictionary data of the message received from the Redis Stream.

**Process:**
1.  **Pre-checks:** Verifies that `_bot` and `_container` are set. Logs errors and returns if they are missing.
2.  **Message Type Extraction:** Extracts the `type` field from `message_data`. Logs a warning and returns if `type` is missing.
3.  **Handler Lookup:** Retrieves all handlers registered for the extracted `message_type`.
4.  **Handler Execution:** Iterates through the matching handlers:
    *   If a `filter_func` is provided, it's executed. If the filter returns `True` (or if no filter is present), the handler is called.
    *   Handlers are called with `message_data` (as `payload`) and `self._container`.
    *   Includes error handling to log exceptions that occur during handler execution.

### `bot_redis_dispatcher`

```python
bot_redis_dispatcher = BotRedisDispatcher()
```
A global instance of `BotRedisDispatcher` is created, making it readily available for registering handlers and processing messages throughout the application.
