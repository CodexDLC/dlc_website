"""
Entry point для Telegram Bot.
Подключается к Backend через HTTP API.
"""

import asyncio
import importlib

from loguru import logger as log
from redis.asyncio import Redis

from src.shared.core.logger import setup_logging
from src.telegram_bot.core.config import BotSettings
from src.telegram_bot.core.container import BotContainer
from src.telegram_bot.core.factory import build_bot
from src.telegram_bot.core.routers import build_main_router
from src.telegram_bot.core.settings import MIDDLEWARE_CLASSES


async def startup(settings: BotSettings) -> None:
    """Инициализация логирования при запуске бота."""
    setup_logging(settings, service_name="telegram_bot")
    log.info("Telegram Bot starting...")
    log.info(f"Backend API: {settings.api_url}")


async def shutdown(container: BotContainer) -> None:
    """Очистка ресурсов при остановке бота."""
    log.info("Shutting down Telegram Bot...")
    await container.shutdown()
    log.info("Bot stopped")


async def main() -> None:
    """Основная функция запуска Telegram Bot."""
    # 1. Загрузка настроек
    settings = BotSettings()  # type: ignore[call-arg]

    # 2. Логирование
    await startup(settings)

    # 3. Redis
    redis_client = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    log.debug("Redis client initialized")

    # 4. DI Container
    container = BotContainer(settings, redis_client)
    log.debug("BotContainer initialized")

    # 5. Bot + Dispatcher
    bot, dp = await build_bot(settings, redis_client)
    container.set_bot(bot)
    log.info("Bot and Dispatcher created")

    # 6. Инициализация ARQ
    await container.init_arq()

    # 7. Middleware (динамическая загрузка из settings.py)
    log.info("Attaching middleware...")
    for mw_module_name in MIDDLEWARE_CLASSES:
        try:
            # Импортируем модуль
            module_path = f"src.telegram_bot.{mw_module_name}"
            module = importlib.import_module(module_path)

            # Ищем функцию setup
            if hasattr(module, "setup"):
                mw_instance = module.setup(container)
                dp.update.middleware(mw_instance)
                log.info(f"Middleware attached: {mw_module_name}")
            else:
                log.warning(f"Middleware module {mw_module_name} has no 'setup' function")

        except ImportError as e:
            log.error(f"Failed to import middleware {mw_module_name}: {e}")
        except Exception as e:
            log.error(f"Failed to setup middleware {mw_module_name}: {e}")

    # 8. Роутеры
    main_router = build_main_router()
    dp.include_router(main_router)
    log.info("Routers attached")

    # 9. Запуск Redis Stream Processor
    await container.stream_processor.start_listening()
    log.info("Redis Stream Processor started.")

    # 10. Polling
    log.info("Bot polling started")
    try:
        await dp.start_polling(
            bot, allowed_updates=["message", "callback_query", "inline_query", "chosen_inline_result"]
        )
    finally:
        await shutdown(container)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot stopped by user")
    except Exception as e:  # noqa: BLE001
        log.critical(f"Critical error: {e}", exc_info=True)
