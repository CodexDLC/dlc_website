from typing import Any
from src.telegram_bot.services.base.base_orchestrator import BaseBotOrchestrator
from src.telegram_bot.services.base.view_dto import UnifiedViewDTO
from src.telegram_bot.features.{feature_key}.ui.ui import {class_name}UI
from src.telegram_bot.features.{feature_key}.feature_setting import {class_name}States

class {class_name}Orchestrator(BaseBotOrchestrator):
    def __init__(self):
        super().__init__(expected_state="{feature_key}")
        self.ui = {class_name}UI()

    async def handle_entry(self, user_id: int, payload: Any = None) -> UnifiedViewDTO:
        \"\"\"Вход в фичу (Cold Start). Вызывается Director или handler.\"\"\"
        # Устанавливаем начальный стейт
        if self._director:
            await self.director.state.set_state({class_name}States.main)
        # Загружаем данные...
        return await self.render(None)

    async def render_content(self, payload: Any) -> Any:
        \"\"\"Отрисовка контента\"\"\"
        return self.ui.render_main(payload)
