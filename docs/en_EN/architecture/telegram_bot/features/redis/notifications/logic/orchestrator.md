# 📜 Orchestrator

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This module defines the `NotificationsOrchestrator` class, which is responsible for processing incoming notification payloads from Redis Streams, validating them, and preparing them for delivery to the appropriate Telegram chat or topic.

## `NotificationsOrchestrator` Class

The `NotificationsOrchestrator` handles the business logic for the Notifications feature, ensuring that notifications are correctly formatted and routed.

### Initialization (`__init__`)

```python
def __init__(self, settings: BotSettings):
```
Initializes the `NotificationsOrchestrator`.

*   `settings` (`BotSettings`): An instance of `BotSettings` containing bot-specific configurations, such as Telegram channel IDs and topic IDs.

**Key Components Initialized:**
*   `self.settings`: Stores the application settings.
*   `self.ui`: An instance of `NotificationsUI`, responsible for rendering the notification messages.

### `handle_notification` Method

```python
def handle_notification(self, raw_payload: dict[str, Any]) -> UnifiedViewDTO:
```
Processes an incoming raw notification payload, validates it, and prepares a `UnifiedViewDTO` for sending.

*   `raw_payload` (dict[str, Any]): The raw dictionary data received from the Redis Stream, expected to conform to the `BookingNotificationPayload` structure.

**Process:**
1.  **Payload Validation:** Attempts to validate the `raw_payload` against the `BookingNotificationPayload` Pydantic model.
2.  **Failure Handling:** If validation fails, it calls `handle_failure` to generate an error notification.
3.  **UI Rendering:** If validation is successful, it uses `self.ui.render_notification` to generate the visual content of the notification.
4.  **Target Determination:** Determines the `target_chat_id` (admin channel) and `message_thread_id` (topic) based on `BotSettings` and the notification's `category_slug`.
5.  **DTO Creation:** Constructs a `UnifiedViewDTO` containing the rendered content, target chat/topic information, and a session key.

**Returns:**
A `UnifiedViewDTO` object ready for dispatch by the `ViewSender`.

### `handle_failure` Method

```python
def handle_failure(self, raw_payload: dict[str, Any], error_msg: str) -> UnifiedViewDTO:
```
Generates a `UnifiedViewDTO` for a notification processing failure. This is used when an incoming notification payload cannot be validated or processed correctly.

*   `raw_payload` (dict[str, Any]): The original raw payload that caused the failure.
*   `error_msg` (str): A string describing the validation or processing error.

**Process:**
1.  Extracts the `booking_id` from the `raw_payload` for identification.
2.  Constructs a descriptive error message indicating the failure.
3.  Creates a `UnifiedViewDTO` with the error message, targeting the admin channel and notification topic.

**Returns:**
A `UnifiedViewDTO` object representing the failure notification.
