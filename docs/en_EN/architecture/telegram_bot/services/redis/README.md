# 📂 Redis Services

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../../README.md)

This directory contains services specifically designed for interacting with Redis, including a custom router for Redis Stream messages, a dispatcher for processing these messages, and a stream processor for listening to Redis Streams.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[📜 Router](./router.md)** | Custom router for handling Redis Stream messages |
| **[📜 Dispatcher](./dispatcher.md)** | Dispatches Redis Stream messages to appropriate handlers |
| **[📜 Stream Processor](./stream_processor.md)** | Listens to and processes messages from Redis Streams |
