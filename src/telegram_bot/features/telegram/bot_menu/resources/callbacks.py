from aiogram.filters.callback_data import CallbackData


class DashboardCallback(CallbackData, prefix="dash"):
    """
    Callback для кнопок дашборда.
    action: действие (nav - навигация, refresh - обновить)
    target: куда переходим (account, settings, etc.)
    """

    action: str
    target: str | None = None
