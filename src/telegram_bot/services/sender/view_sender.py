import contextlib

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from loguru import logger as log

from src.telegram_bot.infrastructure.redis.managers.sender.sender_manager import SenderManager
from src.telegram_bot.services.base import UnifiedViewDTO, ViewResultDTO


class ViewSender:
    """
    Сервис-почтальон.
    Отвечает за отправку и обновление сообщений (Menu и Content).
    """

    def __init__(
        self,
        bot: Bot,
        sender_manager: SenderManager,
    ):
        self.bot = bot
        self.manager = sender_manager

        self.key: int | str | None = None
        self.chat_id: int | str | None = None
        self.is_channel: bool = False
        self.message_thread_id: int | None = None

    async def send(self, view: UnifiedViewDTO):
        """
        Основной метод синхронизации UI.
        """
        if not view.session_key or not view.chat_id:
            log.error("ViewSender: session_key and chat_id are required in UnifiedViewDTO")
            return

        self.key = view.session_key
        self.chat_id = view.chat_id
        self.message_thread_id = view.message_thread_id

        self.is_channel = (
            view.mode in ("channel", "topic")
            or (isinstance(self.chat_id, int) and self.chat_id < 0)
            or str(self.chat_id).startswith("-")
            or self.message_thread_id is not None
        )

        # 1. Удаление триггерного сообщения (например, команды /start)
        if view.trigger_message_id:
            with contextlib.suppress(TelegramAPIError):
                await self.bot.delete_message(chat_id=self.chat_id, message_id=view.trigger_message_id)

        ui_coords = await self.manager.get_coords(self.key, self.is_channel)

        # 2. Очистка старого интерфейса бота
        if view.clean_history:
            await self._delete_previous_interface(ui_coords)
            ui_coords = {}
            await self.manager.clear_coords(self.key, self.is_channel)

        # 3. Обработка Menu и Content
        old_menu_id = ui_coords.get("menu_msg_id")
        new_menu_id = await self._process_message(view_dto=view.menu, old_message_id=old_menu_id, log_prefix="MENU")

        old_content_id = ui_coords.get("content_msg_id")
        new_content_id = await self._process_message(
            view_dto=view.content, old_message_id=old_content_id, log_prefix="CONTENT"
        )

        updates = {}
        if new_menu_id and new_menu_id != old_menu_id:
            updates["menu_msg_id"] = new_menu_id
        if new_content_id and new_content_id != old_content_id:
            updates["content_msg_id"] = new_content_id

        if updates:
            await self.manager.update_coords(self.key, updates, self.is_channel)

    async def _delete_previous_interface(self, ui_coords: dict):
        if not self.chat_id:
            return

        menu_id = ui_coords.get("menu_msg_id")
        content_id = ui_coords.get("content_msg_id")

        if menu_id:
            with contextlib.suppress(TelegramAPIError):
                await self.bot.delete_message(chat_id=self.chat_id, message_id=menu_id)

        if content_id:
            with contextlib.suppress(TelegramAPIError):
                await self.bot.delete_message(chat_id=self.chat_id, message_id=content_id)

    async def _process_message(
        self, view_dto: ViewResultDTO | None, old_message_id: int | None, log_prefix: str
    ) -> int | None:
        if not view_dto or not self.chat_id:
            return old_message_id

        if old_message_id:
            try:
                await self.bot.edit_message_text(
                    chat_id=self.chat_id, message_id=old_message_id, text=view_dto.text, reply_markup=view_dto.kb
                )
                return old_message_id
            except TelegramAPIError:
                pass

        try:
            sent = await self.bot.send_message(
                chat_id=self.chat_id,
                text=view_dto.text,
                reply_markup=view_dto.kb,
                message_thread_id=self.message_thread_id,
            )
            return sent.message_id
        except TelegramAPIError as e:
            log.error(f"ViewSender [{log_prefix}] | Send error: {e}")
            return None
