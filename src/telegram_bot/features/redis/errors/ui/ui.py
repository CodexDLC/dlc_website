from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.telegram_bot.services.base.view_dto import ViewResultDTO


class ErrorUI:
    """
    UI для отображения ошибок.
    """

    def render_error(self, error_config: dict) -> ViewResultDTO:
        title = error_config.get("title", "Error")
        text = error_config.get("text", "Unknown error")
        button_text = error_config.get("button_text", "OK")
        action = error_config.get("action", "refresh")

        # Формируем текст
        full_text = f"<b>{title}</b>\n\n{text}"

        # Формируем кнопку
        builder = InlineKeyboardBuilder()

        # Если action начинается с nav:, это навигация
        # Иначе это просто callback (например, refresh)
        # Для простоты пока используем raw callback data, но лучше через CallbackData
        builder.button(text=button_text, callback_data=action)

        return ViewResultDTO(text=full_text, kb=builder.as_markup())
