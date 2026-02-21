# 📜 Main Application Entry Point (`app_telegram.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This module (`src/telegram_bot/app_telegram.py`) serves as the main entry point for the Telegram Bot application. It orchestrates the entire bot lifecycle, from loading configurations and initializing services to setting up middleware, routers, and starting the polling process.

## Purpose

This file is responsible for:
*   Loading environment settings.
*   Setting up logging.
*   Initializing Redis client and the Dependency Injection (DI) container.
*   Building the Aiogram `Bot` and `Dispatcher` instances.
*   Attaching all necessary middlewares.
*   Including feature-specific routers.
*   Starting the Redis Stream Processor.
*   Initiating the Telegram bot's polling loop.
*   Handling graceful shutdown.

## Functions

### `startup(settings: BotSettings) -> None`

An asynchronous function called at the very beginning of the bot's execution.

*   `settings` (`BotSettings`): The loaded bot settings.

**Process:**
1.  Sets up the logging configuration using `setup_logging()`.
2.  Logs an informational message indicating the bot's startup and the configured Backend API URL.

### `shutdown(container: BotContainer) -> None`

An asynchronous function responsible for gracefully shutting down the bot and releasing resources.

*   `container` (`BotContainer`): The main Dependency Injection container.

**Process:**
1.  Logs an informational message about the shutdown process.
2.  Calls `container.shutdown()` to ensure all services managed by the container (e.g., Redis connections, stream processors) are properly closed.
3.  Logs a final message indicating that the bot has stopped.

### `main() -> None`

The primary asynchronous function that encapsulates the entire bot initialization and execution flow.

**Process:**
1.  **Load Settings:** Instantiates `BotSettings` to load configurations from environment variables.
2.  **Setup Logging:** Calls `startup()` to initialize logging.
3.  **Initialize Redis:** Creates an asynchronous Redis client instance using the `redis_url` from settings.
4.  **Initialize DI Container:** Creates an instance of `BotContainer`, passing the settings and Redis client. The `BotContainer` then initializes various services and orchestrators.
5.  **Build Bot & Dispatcher:** Calls `build_bot()` to create the `aiogram.Bot` and `aiogram.Dispatcher` instances. The `Bot` object is then set in the `container`.
6.  **Attach Middleware:** Attaches a series of middlewares to the `Dispatcher`'s update pipeline. The order of attachment is crucial as middlewares process updates from outside-in:
    *   `UserValidationMiddleware`: Ensures events originate from a valid user.
    *   `ThrottlingMiddleware`: Prevents spam and rate-limits requests.
    *   `SecurityMiddleware`: Protects against user data spoofing.
    *   `ContainerMiddleware`: Injects the `BotContainer` into handler data.
7.  **Attach Routers:** Calls `build_main_router()` to collect and assemble all feature-specific routers, then includes this main router into the `Dispatcher`.
8.  **Start Redis Stream Processor:** Initiates the `RedisStreamProcessor` managed by the `container` to start listening for messages from Redis Streams.
9.  **Start Polling:** Calls `dp.start_polling(bot)` to begin listening for incoming updates from the Telegram API. This is the main loop of the bot.
10. **Graceful Shutdown:** Ensures that `shutdown(container)` is called in a `finally` block, guaranteeing resource cleanup even if polling is interrupted.

## Execution

The script uses `asyncio.run(main())` to execute the asynchronous `main` function. It includes basic error handling for `KeyboardInterrupt` (user-initiated stop) and other critical exceptions.
