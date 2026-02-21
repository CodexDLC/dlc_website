# 📜 Handlers

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This module defines the Redis Stream handlers for processing notification messages. It uses a `RedisRouter` to dispatch incoming messages to specific handler functions based on their type.

## `notifications_router`

```python
notifications_router = RedisRouter()
```
An instance of `RedisRouter` specifically dedicated to registering and dispatching handlers for notification messages received from Redis Streams.

## `handle_new_appointment_notification` Function

```python
@notifications_router.message("new_appointment")
async def handle_new_appointment_notification(message_data: dict[str, Any], container: Any):
```
This asynchronous function is a handler for "new_appointment" messages received from Redis Streams. It is responsible for processing new appointment notifications, validating them, and ensuring their delivery to the appropriate Telegram chat.

*   `message_data` (dict[str, Any]): The data payload of the Redis Stream message, expected to contain details about the new appointment.
*   `container` (`BotContainer`): The Dependency Injection container, providing access to various services and feature orchestrators, specifically the `notifications` orchestrator and `view_sender`.

**Process:**
1.  **Orchestrator and Sender Retrieval:** Retrieves the `notifications` orchestrator and `view_sender` from the `container`.
2.  **Notification Processing:**
    *   Attempts to process the `message_data` using `orchestrator.handle_notification()`. This method is expected to validate the payload and prepare a `UnifiedViewDTO`.
    *   If `orchestrator.handle_notification()` raises an exception (e.g., due to validation failure), it catches the exception and calls `orchestrator.handle_failure()` to generate an emergency notification about the processing error.
3.  **Message Sending:** Uses `view_sender.send()` to dispatch the generated `UnifiedViewDTO` (either the successful notification or the failure notification) to Telegram.
4.  **Critical Error Logging:** Includes a critical error log for any unexpected exceptions that occur within the handler itself, ensuring that unhandled issues are recorded.
