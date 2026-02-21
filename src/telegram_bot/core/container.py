import socket
from typing import Any

from aiogram import Bot
from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from loguru import logger as log
from redis.asyncio import Redis

from src.shared.core.constants import RedisStreams
from src.shared.core.manager_redis.manager import StreamManager
from src.shared.core.redis_service import RedisService
from src.telegram_bot.core.config import BotSettings
from src.telegram_bot.features.telegram.bot_menu.logic.orchestrator import BotMenuOrchestrator
from src.telegram_bot.infrastructure.redis.container import RedisContainer
from src.telegram_bot.services.feature_discovery.service import FeatureDiscoveryService
from src.telegram_bot.services.redis.dispatcher import bot_redis_dispatcher
from src.telegram_bot.services.redis.stream_processor import RedisStreamProcessor
from src.telegram_bot.services.sender.view_sender import ViewSender


class BotContainer:
    """
    DI Container for Telegram Bot.
    Содержит настройки, Redis и клиенты к бэкенду.
    Контракты фич получают реализации отсюда.
    """

    def __init__(self, settings: BotSettings, redis_client: Redis):
        self.settings = settings
        self.redis_client = redis_client
        self.bot: Bot | None = None
        self.view_sender: ViewSender | None = None
        self.arq_pool: ArqRedis | None = None

        # --- Redis Layer (Shared) ---
        self.redis_service = RedisService(redis_client)
        self.stream_manager = StreamManager(self.redis_service)

        # --- Redis Layer (Bot Specific) ---
        self.redis = RedisContainer(redis_client)

        # --- Redis Stream Processor (Worker) ---
        consumer_name = f"{RedisStreams.BotEvents.CONSUMER_PREFIX}{socket.gethostname()}"
        self.stream_processor = RedisStreamProcessor(
            stream_manager=self.stream_manager,
            stream_name=RedisStreams.BotEvents.NAME,
            consumer_group_name=RedisStreams.BotEvents.GROUP,
            consumer_name=consumer_name,
        )

        # --- Services ---
        self.discovery_service = FeatureDiscoveryService()
        self.discovery_service.discover_all()

        # --- Feature Orchestrators ---
        self.features: dict[str, Any] = {}

        # Создаём оркестраторы и регистрируем их как атрибуты контейнера
        discovered_orchestrators = self.discovery_service.create_feature_orchestrators(self)
        for key, instance in discovered_orchestrators.items():
            self.features[key] = instance
            setattr(self, key, instance)

        # --- Core Features ---
        self.bot_menu = BotMenuOrchestrator(
            discovery_provider=self.discovery_service,
            settings=self.settings,
        )
        self.features["bot_menu"] = self.bot_menu

        log.info(f"BotContainer | initialized features={list(self.features.keys())}")

    async def init_arq(self) -> None:
        """Инициализация пула ARQ для постановки задач воркеру."""
        self.arq_pool = await create_pool(
            RedisSettings(
                host=self.settings.effective_redis_host,
                port=self.settings.redis_port,
                password=self.settings.redis_password,
                database=0,
            )
        )
        log.info("BotContainer | ARQ pool initialized.")

    def set_bot(self, bot: Bot) -> None:
        """Устанавливает объект Bot в контейнер и инициализирует BotRedisDispatcher."""
        self.bot = bot
        self.view_sender = ViewSender(bot=self.bot, sender_manager=self.redis.sender)

        bot_redis_dispatcher.set_bot(self.bot)
        bot_redis_dispatcher.set_container(self)
        self.stream_processor.set_message_callback(bot_redis_dispatcher.process_message)

        log.debug("Bot object set and BotRedisDispatcher initialized in BotContainer.")

    async def shutdown(self):
        """Закрытие ресурсов."""
        if self.stream_processor:
            await self.stream_processor.stop_listening()
        if self.arq_pool:
            await self.arq_pool.close()
        if self.redis_client:
            await self.redis_client.close()
