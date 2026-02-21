from typing import Any
from .texts import {class_name}Texts

class {class_name}Formatter:
    """
    Форматирование сообщений для фичи {class_name}.
    """

    def format_main(self, payload: Any) -> str:
        """
        Формирует текст главного экрана.
        """
        # Пример использования payload
        user_name = payload.get("name", "User") if isinstance(payload, dict) else "User"

        return (
            f"{{{class_name}Texts.TITLE}}\n\n"
            f"{{{class_name}Texts.DESCRIPTION}}\n"
            f"User: {{user_name}}"
        )
