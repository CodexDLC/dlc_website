import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger as log

from src.shared.core.manager_redis.manager import StreamManager


class RedisStreamProcessor:
    """
    Процессор для чтения сообщений из Redis Stream.
    Использует StreamManager для работы с Redis.
    Отвечает за цикл опроса (Polling Loop) и вызов callback-функции.
    """

    def __init__(
        self,
        stream_manager: StreamManager,
        stream_name: str,
        consumer_group_name: str,
        consumer_name: str,
        batch_count: int = 10,
        poll_interval: float = 1.0,
    ):
        self.stream_manager = stream_manager
        self.stream_name = stream_name
        self.group_name = consumer_group_name
        self.consumer_name = consumer_name
        self.batch_count = batch_count
        self.poll_interval = poll_interval

        self.is_running = False
        self._message_callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None

    def set_message_callback(self, callback: Callable[[dict[str, Any]], Awaitable[None]]):
        """Устанавливает функцию обратного вызова для обработки сообщений."""
        self._message_callback = callback

    async def start_listening(self):
        """Запускает цикл чтения стрима."""
        if self.is_running:
            log.warning("RedisStreamProcessor is already running.")
            return

        # Создаем группу потребителей (если нет)
        await self.stream_manager.create_group(self.stream_name, self.group_name)

        self.is_running = True
        asyncio.create_task(self._consume_loop())
        log.info(
            f"RedisStreamProcessor started listening to manager_redis '{self.stream_name}' as '{self.consumer_name}'"
        )

    async def stop_listening(self):
        """Останавливает цикл чтения."""
        self.is_running = False
        log.info("RedisStreamProcessor stopped.")

    async def _consume_loop(self):
        """Бесконечный цикл чтения сообщений."""
        while self.is_running:
            try:
                # Читаем новые сообщения через менеджер
                messages = await self.stream_manager.read_events(
                    stream_name=self.stream_name,
                    group_name=self.group_name,
                    consumer_name=self.consumer_name,
                    count=self.batch_count,
                )

                if not messages:
                    # Если сообщений нет, ждем интервал
                    await asyncio.sleep(self.poll_interval)
                    continue

                for message_id, data in messages:
                    await self._process_single_message(message_id, data)

            except Exception as e:
                log.error(f"Error in RedisStreamProcessor loop: {e}")
                await asyncio.sleep(5)  # Пауза при ошибке

    async def _process_single_message(self, message_id: str, data: dict[str, Any]):
        """Обрабатывает одно сообщение и подтверждает его (ACK)."""
        try:
            if self._message_callback:
                await self._message_callback(data)

            # Подтверждаем обработку через менеджер
            await self.stream_manager.ack_event(self.stream_name, self.group_name, message_id)

        except Exception as e:
            log.error(f"Failed to process message {message_id}: {e}")
