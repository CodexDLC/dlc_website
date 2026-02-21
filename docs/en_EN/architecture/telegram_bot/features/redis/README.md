# 📂 Redis Features

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../README.md)

Redis features are "listener" modules that do not interact with users via commands. Instead, they consume events from Redis Streams (sent by the Backend or Workers) and perform actions in Telegram.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[📂 Notifications](./notifications/README.md)** | Consumes booking events and routes them to Telegram Topics |
| **[📂 Errors](./errors/README.md)** | Consumes system errors and notifies developers |

## 🔄 How it Works

1.  **Event Source**: The Django Backend or a Worker pushes a message to a Redis Stream (e.g., `bot_events`).
2.  **Stream Processor**: The `RedisStreamProcessor` (in `core/container.py`) listens for new messages.
3.  **Dispatcher**: The `bot_redis_dispatcher` identifies the feature responsible for the event type.
4.  **Orchestrator**: The feature's orchestrator validates the data and prepares a `UnifiedViewDTO`.
5.  **Delivery**: The `ViewSender` delivers the message to the target Telegram chat/topic.
