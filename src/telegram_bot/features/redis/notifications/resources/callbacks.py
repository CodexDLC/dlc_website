from aiogram.filters.callback_data import CallbackData


class NotificationsCallback(CallbackData, prefix="notifications"):
    """
    CallbackData для фичи Notifications.
    action: действие (approve, reject, etc.)
    session_id: идентификатор брони (или сессии)
    topic_id: идентификатор топика в Telegram (для редактирования сообщений)
    """

    action: str
    session_id: int | str | None = None
    topic_id: int | None = None
