from typing import TYPE_CHECKING, Any, cast

from src.shared.schemas.response import CoreResponseDTO
from src.telegram_bot.services.base.view_dto import UnifiedViewDTO

if TYPE_CHECKING:
    from src.telegram_bot.services.director.director import Director


class BaseBotOrchestrator:
    """
    Базовый класс оркестратора.
    """

    def __init__(self, expected_state: str | None):
        self.expected_state = expected_state
        self._director: Director | None = None

    def set_director(self, director: "Director") -> None:
        self._director = director

    @property
    def director(self) -> "Director":
        if not self._director:
            raise RuntimeError(f"Director not set for {self.__class__.__name__}")
        return self._director

    async def handle_entry(self, user_id: int, chat_id: int | None = None, payload: Any = None) -> UnifiedViewDTO:
        """
        Точка входа в фичу. Теперь поддерживает chat_id.
        """
        return await self.render(payload)

    async def render_content(self, payload: Any) -> Any:
        raise NotImplementedError(f"render_content not implemented in {self.__class__.__name__}")

    async def render(self, payload: Any) -> UnifiedViewDTO:
        if isinstance(payload, CoreResponseDTO):
            return await self.process_response(payload)

        content_view = await self.render_content(payload)
        return UnifiedViewDTO(content=content_view, menu=None)

    async def process_response(self, response: CoreResponseDTO) -> UnifiedViewDTO:
        if response.header.next_state and response.header.next_state != self.expected_state:
            result = await self.director.set_scene(feature=response.header.next_state, payload=response.payload)
            return cast("UnifiedViewDTO", result)

        content_view = None
        if response.payload is not None:
            content_view = await self.render_content(response.payload)

        return UnifiedViewDTO(content=content_view, menu=None)
