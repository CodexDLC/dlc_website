# 📄 DI Container

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The `BotContainer` is the Dependency Injection (DI) hub for the Telegram Bot. It initializes and holds references to settings, Redis clients, services, and feature orchestrators.

## 🏗️ Class: BotContainer

Located in: `src/telegram_bot/core/container.py`

### Initialization

```python
def __init__(self, settings: BotSettings, redis_client: Redis)
```

During initialization, the container:
1.  **Sets up Redis Layers**: Initializes `RedisService`, `StreamManager`, and the bot-specific `RedisContainer`.
2.  **Initializes Stream Processor**: Sets up `RedisStreamProcessor` to listen for events (e.g., notifications from the backend).
3.  **Discovers Features**: Uses `FeatureDiscoveryService` to automatically find and instantiate feature orchestrators.
4.  **Registers Features**: Dynamically adds discovered orchestrators as attributes to the container instance.

### Key Components

- **settings**: Instance of `BotSettings`.
- **redis_client**: The raw `redis.asyncio` client.
- **bot**: The `aiogram.Bot` instance (set after factory initialization).
- **view_sender**: A `ViewSender` service for smart message editing and sending.
- **arq_pool**: A pool for `ARQ` to enqueue background tasks for the worker.
- **stream_processor**: Handles incoming Redis Stream messages (e.g., for routing notifications to specific users).
- **discovery_service**: Manages the auto-discovery of bot features and their menu configurations.

### Methods

#### `init_arq()`
Asynchronously initializes the ARQ pool using Redis settings from the configuration.

#### `set_bot(bot: Bot)`
Injects the `Bot` instance into the container and links it with the `ViewSender` and `BotRedisDispatcher`. This is typically called during the bot's startup sequence.

#### `shutdown()`
Gracefully closes resources, including the stream processor, ARQ pool, and Redis client.

## 🧩 Feature Access

Features are accessible via the `features` dictionary or directly as attributes:
```python
# Accessing the bot menu orchestrator
menu = container.bot_menu
# or
menu = container.features["bot_menu"]
```
