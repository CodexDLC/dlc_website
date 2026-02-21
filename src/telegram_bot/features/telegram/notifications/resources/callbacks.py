# Импортируем базовый колбэк из Redis-фичи
from src.telegram_bot.features.redis.notifications.resources.callbacks import NotificationsCallback

# Экспортируем его под тем же именем
__all__ = ["NotificationsCallback"]
