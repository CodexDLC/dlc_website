# 📄 Bot Factory

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The `Bot Factory` is responsible for creating and configuring the core `aiogram` components: the `Bot` and the `Dispatcher`.

## 🛠️ Function: build_bot

Located in: `src/telegram_bot/core/factory.py`

```python
async def build_bot(settings: BotSettings, redis_client: Redis) -> tuple[Bot, Dispatcher]
```

### Responsibilities

1.  **Token Validation**: Checks if `BOT_TOKEN` is present in the settings. Raises a `RuntimeError` if missing.
2.  **Bot Initialization**: Creates an `aiogram.Bot` instance with `HTML` as the default parse mode.
3.  **Redis Connectivity Check**: Performs a `ping` on the provided Redis client to ensure the bot can store FSM states and handle caching.
4.  **Storage Setup**: Initializes `RedisStorage` using the verified Redis client. This storage is used by the Dispatcher for Finite State Machine (FSM) data.
5.  **Dispatcher Initialization**: Creates an `aiogram.Dispatcher` instance, injecting the Redis storage and bot settings.

### Error Handling

- **RuntimeError (Token)**: If the bot token is not configured.
- **RuntimeError (Redis)**: If a connection to Redis cannot be established. This prevents the bot from starting in a broken state where FSM would fail.

## 📝 Usage Example

```python
settings = BotSettings()
redis = Redis.from_url(settings.redis_url)

bot, dp = await build_bot(settings, redis)
```
