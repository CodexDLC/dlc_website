# 📜 Throttling

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `ThrottlingMiddleware`, an Aiogram middleware designed to protect the bot from spam and flood attacks by implementing rate limiting. It uses Redis to track and block users who send requests too frequently.

## `ThrottlingMiddleware` Class

The `ThrottlingMiddleware` is essential for maintaining the bot's stability and responsiveness by preventing a single user from overwhelming the system with excessive requests.

### Initialization (`__init__`)

```python
def __init__(self, redis: Redis, rate_limit: float = 1.0):
```
Initializes the `ThrottlingMiddleware`.

*   `redis` (`Redis`): An instance of the asynchronous Redis client, used for storing throttling keys.
*   `rate_limit` (`float`): The minimum interval (in seconds) required between requests from the same user (default: `1.0`).

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
*   `event` (`TelegramObject`): The incoming Telegram event object (e.g., `Message`, `CallbackQuery`).
*   `data` (`dict[str, Any]`): A dictionary containing various data passed through the middleware chain.

**Process:**
1.  **Extract User ID:** Attempts to extract the `user_id` from the `event.from_user` object if the event is a `Message` or `CallbackQuery`.
2.  **Bypass Check:** If `user_id` cannot be determined (e.g., for system events), the middleware bypasses throttling and passes the event to the next handler.
3.  **Redis Key Check:** Constructs a Redis key (e.g., `throttle:{user_id}`) and checks if it exists in Redis.
4.  **Throttling Logic:**
    *   If the key exists, it means the user has sent a request too recently. The middleware logs a warning, and if the event is a `CallbackQuery`, it sends a silent alert to the user. The processing of the event is then interrupted by returning `None`.
    *   If the key does not exist, the request is allowed. A new key is set in Redis with an expiration time (`ex`) equal to the `rate_limit`, preventing further requests from that user until the key expires.
5.  **Pass to Next Handler:** If the request is not throttled, the event is passed to the `handler` for further processing.

**Returns:**
`Any`: The result of the `handler` if the request is allowed, or `None` if the request is throttled.
