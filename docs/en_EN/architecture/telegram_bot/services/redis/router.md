# 📜 Router

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `RedisRouter` class, a custom router designed for grouping and dispatching handlers for Redis Stream messages. It enables the creation of modular and organized event handlers for various types of Redis Stream events.

## `RedisRouter` Class

The `RedisRouter` provides a decorator-based mechanism to register functions that should process specific types of messages received from Redis Streams.

### Initialization (`__init__`)

```python
def __init__(self):
```
Initializes the `RedisRouter`.

**Key Action:**
*   Initializes `self._handlers` as an empty dictionary. This dictionary will store registered handlers, mapped by `message_type`. Each `message_type` can have a list of `(handler_func, filter_func)` tuples.

### `message` Method (Decorator)

```python
def message(self, message_type: str, filter_func: Callable[[dict[str, Any]], bool] | None = None):
```
This method acts as a decorator, allowing you to register a function as a handler for a specific `message_type` from a Redis Stream.

*   `message_type` (`str`): The type of message this handler should process (e.g., "new_appointment", "system_error").
*   `filter_func` (`Callable[[dict[str, Any]], bool] | None`): An optional callable that takes the message payload as an argument and returns `True` if the handler should process the message, or `False` otherwise. This allows for more granular control over message dispatching.

**Usage:**
```python
@redis_router.message("my_message_type", filter_func=my_custom_filter)
async def my_handler(payload: dict[str, Any], container: Any):
    # ... process message ...
```

**Returns:**
A decorator function that registers the decorated handler.

### `handlers` Property

```python
@property
def handlers(self):
```
A property that returns the dictionary of all registered handlers.

**Returns:**
`dict[str, list[tuple[Callable[[dict[str, Any], Any], Any], Callable[[dict[str, Any]], bool] | None]]]`: A dictionary where keys are `message_type` strings, and values are lists of `(handler_func, filter_func)` tuples.
