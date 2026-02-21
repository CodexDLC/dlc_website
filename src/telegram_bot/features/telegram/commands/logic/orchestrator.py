"""
Оркестратор фичи commands.
"""

from typing import Any

from aiogram.types import User

from src.shared.schemas.user import UserUpsertDTO
from src.telegram_bot.core.config import BotSettings
from src.telegram_bot.features.telegram.commands.contracts.commands_contract import AuthDataProvider
from src.telegram_bot.features.telegram.commands.ui.commands_ui import CommandsUI
from src.telegram_bot.services.base.base_orchestrator import BaseBotOrchestrator
from src.telegram_bot.services.base.view_dto import UnifiedViewDTO


class StartOrchestrator(BaseBotOrchestrator):
    """
    Оркестратор стартового экрана (Welcome Screen).
    """

    def __init__(self, auth_provider: AuthDataProvider, ui: CommandsUI, settings: BotSettings):
        super().__init__(expected_state=None)
        self.auth = auth_provider
        self.ui = ui
        self.settings = settings

    async def render(self, payload: Any = None) -> UnifiedViewDTO:
        """
        Стандартный метод рендеринга.
        """
        # Если в payload передано имя пользователя, используем его, иначе дефолт
        user_name = payload if isinstance(payload, str) else "User"

        # В реальном приложении здесь можно было бы получить user_id из контекста
        # Но для простоты мы предполагаем, что render вызывается после handle_entry
        # где мы уже знаем, кто это.

        # ВАЖНО: Для соответствия сигнатуре BaseBotOrchestrator мы не можем
        # принимать здесь user_id. Поэтому используем заглушку или контекст.
        return await self.render_welcome(user_id=0, user_name=user_name)

    async def render_welcome(self, user_id: int, user_name: str = "User") -> UnifiedViewDTO:
        """Внутренний метод для отрисовки приветствия."""
        is_admin = user_id in self.settings.owner_ids_list or user_id in self.settings.superuser_ids_list

        menu_view = self.ui.render_welcome_screen(user_name, is_admin=is_admin)

        return UnifiedViewDTO(
            menu=menu_view,
            content=None,
            clean_history=True,
            chat_id=user_id,
            session_key=user_id,
        )

    async def handle_entry(self, user_id: int, chat_id: int | None = None, payload: Any = None) -> UnifiedViewDTO:
        """
        Точка входа.
        """
        user: User | None = payload if isinstance(payload, User) else None

        if user:
            user_dto = UserUpsertDTO(
                telegram_id=user.id,
                first_name=user.first_name,
                username=user.username,
                last_name=user.last_name,
                language_code=user.language_code,
                is_premium=bool(user.is_premium),
            )
            await self.auth.upsert_user(user_dto)
            user_name = user.first_name or "User"
        else:
            user_name = "User"

        return await self.render_welcome(user_id=user_id, user_name=user_name)
