from aiogram.filters.callback_data import CallbackData

# Если это ПАРНАЯ фича (обработка кнопок из Redis-уведомлений):
# 1. Импортируйте базовый колбэк:
# from src.telegram_bot.features.redis.{feature_key}.resources.callbacks import {class_name}Callback as BaseCallback
# 2. Наследуйтесь БЕЗ указания нового префикса (чтобы поймать те же события):
# class {class_name}Callback(BaseCallback):
#     pass

# Если это САМОСТОЯТЕЛЬНАЯ фича:
class {class_name}Callback(CallbackData, prefix="{feature_key}"):
    """
    Колбэк для фичи {class_name}.
    """
    action: str
    id: str | int
