# 📂 Redis Notifications

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../../README.md)

The `redis/notifications` feature is responsible for receiving booking events from the Redis Stream and delivering them as formatted messages to specific Telegram Topics.

## 🏗️ Architecture

Located in: `src/telegram_bot/features/redis/notifications`

### Orchestrator: `NotificationsOrchestrator`
The core logic for processing incoming Redis events.
- **Validation**: Uses Pydantic (`BookingNotificationPayload`) to ensure the incoming data is valid.
- **Routing**: Determines the target Telegram Topic ID based on the `category_slug` of the service.
- **Error Handling**: If validation fails, it sends a fallback error message to the admin channel.

### UI: `NotificationsUI`
Renders the notification message.
- **Formatting**: Transforms the booking data into a human-readable HTML message for Telegram.

## 📋 feature_setting.py

```python
# Redis features are registered in core/settings.py under INSTALLED_REDIS_FEATURES
```

## 🔄 Logic Flow

1.  **Message Received**: A raw dictionary arrives from the Redis Stream.
2.  **Validation**: `NotificationsOrchestrator` converts the dict into a `BookingNotificationPayload`.
3.  **Topic Selection**:
    - Looks up `category_slug` in `settings.telegram_topics`.
    - If found, uses the specific Topic ID.
    - If not found, defaults to `telegram_notification_topic_id`.
4.  **Rendering**: `NotificationsUI` generates the HTML text.
5.  **Dispatch**: Returns a `UnifiedViewDTO` with `mode="topic"` to the dispatcher for delivery.
