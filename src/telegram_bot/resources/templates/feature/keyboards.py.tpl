from aiogram.utils.keyboard import InlineKeyboardBuilder
from .callbacks import {class_name}Callback
from .texts import {class_name}Texts

def build_main_kb():
    """
    Клавиатура главного экрана.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text={class_name}Texts.BUTTON_ACTION,
        callback_data={class_name}Callback(action="action").pack()
    )

    # Пример кнопки назад (если нужна)
    # builder.button(
    #     text={class_name}Texts.BUTTON_BACK,
    #     callback_data={class_name}Callback(action="back").pack()
    # )

    builder.adjust(1)
    return builder.as_markup()
