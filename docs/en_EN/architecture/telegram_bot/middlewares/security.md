# 📜 Security

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `SecurityMiddleware`, an Aiogram middleware designed to protect against potential user data spoofing or session hijacking attempts. It ensures that the `user_id` associated with an incoming event matches the `user_id` stored in the user's FSM (Finite State Machine) state.

## `SecurityMiddleware` Class

The `SecurityMiddleware` is a critical component for maintaining the integrity and security of user sessions within the bot.

### `__call__` Method

```python
async def __call__(
    self,
    handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
    event: TelegramObject,
    data: dict[str, Any],
) -> Any:
```
This asynchronous method is the entry point for the middleware. It intercepts incoming `TelegramObject` events (e.g., messages, callback queries) before they are processed by the main handlers.

*   `handler` (`Callable`): The next handler in the middleware chain or the final message handler.
*   `event` (`TelegramObject`): The incoming Telegram event object.
*   `data` (`dict[str, Any]`): A dictionary containing various data passed through the middleware chain, including `user` and `state`.

**Process:**
1.  **Extract User and State:** Retrieves the `user` object and `FSMContext` (`state`) from the `data` dictionary.
2  **Bypass Check:** If either `user` or `state` is missing, the middleware bypasses the security check and passes the event to the next handler.
3.  **Retrieve Stored User ID:** Fetches the `session_data` from the FSM state and extracts the `user_id` that was previously stored.
4.  **User ID Mismatch Check:**
    *   If a `stored_user_id` exists and it does not match the `user.id` from the current event, it logs an error indicating a possible session hijacking attempt.
    *   If the `event` is a `CallbackQuery`, it sends an alert to the user about the security error.
    *   In case of a mismatch, the middleware returns `None`, effectively stopping further processing of the event.
5.  **Pass to Next Handler:** If no security issues are detected, the event is passed to the `handler` for further processing.

**Returns:**
`Any`: The result of the `handler` if the security check passes, or `None` if a security mismatch is detected and processing is halted.
