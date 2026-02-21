from typing import Any
from src.telegram_bot.services.base.view_dto import ViewResultDTO
from src.telegram_bot.features.{feature_key}.resources.formatters import {class_name}Formatter
from src.telegram_bot.features.{feature_key}.resources.keyboards import build_main_kb

class {class_name}UI:
    """
    UI сервис для фичи {class_name}.
    Использует форматтеры и клавиатуры из ресурсов.
    """
    def __init__(self):
        self.formatter = {class_name}Formatter()

    def render_main(self, payload: Any) -> ViewResultDTO:
        text = self.formatter.format_main(payload)
        kb = build_main_kb()

        return ViewResultDTO(text=text, kb=kb)
