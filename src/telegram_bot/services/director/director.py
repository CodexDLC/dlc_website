"""
Director — координатор переходов между фичами.
Управляет FSM стейтами и делегирует рендеринг оркестраторам.
"""

from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

from aiogram.fsm.context import FSMContext
from loguru import logger

KEY_SESSION_DATA = "session_data"

if TYPE_CHECKING:
    from src.telegram_bot.core.container import BotContainer


@runtime_checkable
class OrchestratorProtocol(Protocol):
    async def render(self, payload: Any) -> Any: ...
    async def handle_entry(self, user_id: int | None, chat_id: int | None = None, payload: Any = None) -> Any: ...
    def set_director(self, director: Any): ...


class Director:
    """
    Координатор переходов между фичами.
    """

    def __init__(
        self,
        container: "BotContainer",
        state: FSMContext | None = None,
        user_id: int | None = None,
        chat_id: int | None = None,
    ):
        self.container = container
        self.state = state
        self.user_id = user_id
        self.chat_id = chat_id

    async def set_scene(self, feature: str, payload: Any) -> Any:
        """
        Межфичевый переход: смена FSM State + вызов entry logic.
        """
        orchestrator = self.container.features.get(feature)

        if not orchestrator:
            logger.error(f"Director | unknown_feature='{feature}' user_id={self.user_id}")
            return None

        orchestrator = cast("OrchestratorProtocol", orchestrator)
        if hasattr(orchestrator, "set_director"):
            orchestrator.set_director(self)

        # Вызываем handle_entry, прокидывая и user_id, и chat_id
        if hasattr(orchestrator, "handle_entry"):
            return await orchestrator.handle_entry(user_id=self.user_id, chat_id=self.chat_id, payload=payload)

        return await orchestrator.render(payload)

    async def render(self, feature: str, service: str, payload: Any) -> Any:
        return await self.set_scene(feature, payload)
