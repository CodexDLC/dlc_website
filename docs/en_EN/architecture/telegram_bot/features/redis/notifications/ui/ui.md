# 📜 UI

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This module defines the `NotificationsUI` class, which is responsible for rendering notification messages and generating corresponding user interface elements, such as inline keyboards.

## `NotificationsUI` Class

The `NotificationsUI` class provides methods to construct a `ViewResultDTO` based on a notification payload, allowing for dynamic display of notification messages to the user.

### `render_notification` Method

```python
def render_notification(self, payload: BookingNotificationPayload) -> ViewResultDTO:
```
Renders a notification message and an inline keyboard based on the provided `BookingNotificationPayload`.

*   `payload` (`BookingNotificationPayload`): An instance of `BookingNotificationPayload` containing the data for the notification.

**Process:**
1.  **Text Formatting:** Uses `format_new_booking()` from `resources.formatters` to generate the main text content of the notification based on the `payload`.
2.  **Keyboard Building:** Uses `build_main_kb()` from `resources.keyboards` to create an inline keyboard, typically including actions related to the notification (e.g., viewing details, confirming).
3.  **DTO Creation:** Returns a `ViewResultDTO` containing the formatted text and the generated inline keyboard markup.

**Returns:**
A `ViewResultDTO` object ready to be sent to the user.
