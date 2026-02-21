from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter

from src.telegram_bot.core.container import BotContainer
from src.telegram_bot.services.director.director import Director
from src.telegram_bot.services.sender.view_sender import ViewSender
from src.telegram_bot.features.{feature_type}.{feature_key}.feature_setting import {class_name}States
from src.telegram_bot.features.{feature_type}.{feature_key}.resources.callbacks import {class_name}Callback

router = Router(name="{feature_key}_router")

@router.callback_query(
    {class_name}Callback.filter(F.action == "action"),
    StateFilter({class_name}States.main)
)
async def handle_action(
    call: CallbackQuery,
    callback_data: {class_name}Callback,
    state,
    container: BotContainer
):
    await call.answer()

    # 1. Получаем готовый оркестратор из контейнера
    orchestrator = container.features["{feature_key}"]

    # 2. Инициализируем Директора
    director = Director(container, state, call.from_user.id)
    orchestrator.set_director(director)

    # 3. Вызываем бизнес-логику
    view_dto = await orchestrator.handle_action(callback_data)

    # 4. Отправляем ответ
    await container.view_sender.send(view_dto)
