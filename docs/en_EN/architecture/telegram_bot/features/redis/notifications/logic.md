# 🧠 Notifications Logic (Orchestrator)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The `NotificationsOrchestrator` handles the transformation of raw Redis Stream data into actionable Telegram messages.

## 🏗️ Class: NotificationsOrchestrator

Located in: `src/telegram_bot/features/redis/notifications/logic/orchestrator.py`

### Methods

#### `handle_notification(raw_payload: dict[str, Any]) -> UnifiedViewDTO`

The main entry point for processing a notification.

1.  **Validation**: Attempts to instantiate `BookingNotificationPayload`.
2.  **Routing Logic**:
    - Fetches `telegram_admin_channel_id` as the base chat.
    - Checks `payload.category_slug`.
    - If a mapping exists in `settings.telegram_topics`, it overrides the `message_thread_id`.
3.  **Rendering**: Calls `self.ui.render_notification`.
4.  **Result**: Returns a `UnifiedViewDTO` configured for "topic" mode.

#### `handle_failure(raw_payload: dict, error_msg: str) -> UnifiedViewDTO`

Fallback method used when validation fails. It ensures that the admin is still notified that *something* happened, even if the data was malformed.

---

## 📦 Data Transfer Object (DTO)

Located in: `src/telegram_bot/features/redis/notifications/resources/dto.py`

### `BookingNotificationPayload`

| Field | Type | Description |
|:---|:---|:---|
| `id` | `int` | Booking ID from the database |
| `client_name` | `str` | Full name of the client |
| `client_phone` | `str` | Contact phone number |
| `service_name` | `str` | Name of the booked service |
| `master_name` | `str` | Name of the assigned master |
| `datetime` | `str` | Formatted date and time of the appointment |
| `price` | `float` | Total price |
| `category_slug` | `str` | Used for routing to specific Telegram Topics |
