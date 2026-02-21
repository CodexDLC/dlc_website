# 📜 User Validation

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `UserValidationMiddleware`, an Aiogram middleware responsible for validating the presence of a user in incoming events. It prevents events without an associated user (e.g., from other bots or system events) from being processed by the bot's handlers, and injects the `user` object into the handler's data.

## `UserValidationMiddleware` Class

The `UserValidationMiddleware` ensures that all processed events originate from a legitimate user, simplifying handler logic and preventing unintended processing of non-user-initiated events.

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
1.  **Extract User:** Attempts to extract the `user` object from the `event.from_user` attribute if the event is a `Message` or `CallbackQuery`.
2.  **User Presence Check:**
    *   If no `user` object can be extracted, the middleware logs a warning and returns `None`, effectively stopping the processing of the event. This prevents handlers from receiving events that are not directly from a user.
3.  **Inject User:** If a `user` object is successfully extracted, it is added to the `data` dictionary under the key `"user"`. This makes the `user` object readily available to subsequent middlewares and the final handler without needing to re-extract it.
4.  **Pass to Next Handler:** The event and the augmented `data` dictionary are then passed to the `handler` for further processing.

**Returns:**
`Any`: The result of the `handler` if a user is present and the event is processed, or `None` if no user is found and processing is halted.
