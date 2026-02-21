from aiogram import Router
from aiogram.types import CallbackQuery

from src.telegram_bot.core.container import BotContainer
from src.telegram_bot.services.director.director import Director

from ..resources.callbacks import NotificationsCallback

router = Router(name="notifications_ui_router")


@router.callback_query(NotificationsCallback.filter())
async def handle_action_approve(
    call: CallbackQuery, callback_data: NotificationsCallback, state, container: BotContainer
):
    """
    Единый хендлер для всех callback-действий уведомлений.
    """
    await call.answer()

    orchestrator = container.features.get("notifications")
    if not orchestrator:
        return

    # Инициализируем Директора (хотя в этой фиче навигация пока не используется)
    director = Director(container, state, call.from_user.id)
    orchestrator.set_director(director)

    # Вызываем бизнес-логику
    view_dto = await orchestrator.handle_action(callback_data, call)

    # Отправляем ответ через ViewSender
    if container.view_sender:
        await container.view_sender.send(view_dto)
