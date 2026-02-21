# 📜 Container

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `RedisContainer` class, which acts as a Dependency Injection (DI) container for all Redis-related managers and services within the Telegram bot application. It provides a centralized access point to the Redis data layer.

## `RedisContainer` Class

The `RedisContainer` is responsible for initializing and holding instances of various Redis managers, making them easily accessible throughout the application.

### Initialization (`__init__`)

```python
def __init__(self, redis_client: Redis):
```
Initializes the `RedisContainer` with a Redis client and sets up various Redis managers.

*   `redis_client` (`Redis`): An instance of the asynchronous Redis client.

**Key Components Initialized:**
1.  **Base Service (Wrapper)**:
    *   `self.service` (`RedisService`): An instance of `RedisService` that wraps the raw `redis_client`, providing a higher-level interface for Redis operations.
2.  **Managers**:
    *   `self.sender` (`SenderManager`): An instance of `SenderManager` responsible for managing UI coordinates and message sending-related data in Redis.

**Extensibility:**
The `RedisContainer` is designed to be easily extensible, allowing for the addition of other Redis managers (e.g., `AccountManager`, `BookingManager`) as needed.
