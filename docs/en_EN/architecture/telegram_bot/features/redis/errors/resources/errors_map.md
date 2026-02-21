# 📜 Errors Map

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This module defines the `DEFAULT_ERRORS` dictionary, which serves as a registry for predefined error messages and their associated UI configurations. This map can be extended with custom error definitions if needed.

## `DEFAULT_ERRORS` Dictionary

The `DEFAULT_ERRORS` dictionary stores various error configurations, each identified by a unique key (e.g., "default", "not_found"). Each error configuration is itself a dictionary with the following structure:

*   `"title"` (str): The title of the error message displayed to the user.
*   `"text"` (str): The main body or description of the error.
*   `"button_text"` (str): The text displayed on the inline button associated with the error.
*   `"action"` (str): The callback data or navigation command associated with the inline button. This can trigger a simple callback (e.g., "refresh") or a navigation action (e.g., "nav:menu").

### Examples of Predefined Errors:

*   **"default"**:
    *   `title`: "⚠️ Ошибка"
    *   `text`: "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."
    *   `button_text`: "🔄 Обновить"
    *   `action`: "refresh"
*   **"not_found"**:
    *   `title`: "🔍 Не найдено"
    *   `text`: "Запрашиваемый объект не найден."
    *   `button_text`: "🔙 В меню"
    *   `action`: "nav:menu"
*   **"permission_denied"**:
    *   `title`: "⛔ Доступ запрещен"
    *   `text`: "У вас недостаточно прав для выполнения этого действия."
    *   `button_text`: "🔙 Назад"
    *   `action`: "back"
*   **"maintenance"**:
    *   `title`: "🛠 Технические работы"
    *   `text`: "Бот находится на обслуживании. Мы скоро вернемся!"
    *   `button_text`: "🔄 Проверить"
    *   `action`: "refresh"
