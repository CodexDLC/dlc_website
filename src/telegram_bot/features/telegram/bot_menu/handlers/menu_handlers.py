from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from src.telegram_bot.core.container import BotContainer
from src.telegram_bot.features.telegram.bot_menu.resources.callbacks import DashboardCallback
from src.telegram_bot.features.telegram.bot_menu.resources.dto import MenuContext
from src.telegram_bot.services.director.director import Director
from src.telegram_bot.services.helper.context_helper import ContextHelper

router = Router(name="bot_menu_router")


@router.callback_query(DashboardCallback.filter())
async def handle_dashboard_callback(
    call: CallbackQuery, callback_data: DashboardCallback, state: FSMContext, container: BotContainer
):
    """
    Универсальный хендлер для всех действий дашборда.
    """
    await call.answer()

    orchestrator = container.features.get("bot_menu")
    if not orchestrator:
        return

    # 1. Извлекаем базовый контекст
    base_ctx = ContextHelper.extract_base_context(call)

    # 2. Создаем специфичный контекст для меню
    ctx = MenuContext(**base_ctx.model_dump(), action=callback_data.action, target=callback_data.target)

    # 3. Инициализируем Director с chat_id
    director = Director(container=container, state=state, user_id=ctx.user_id, chat_id=ctx.chat_id)
    orchestrator.set_director(director)

    # 4. Вызываем оркестратор
    view_dto = await orchestrator.handle_callback(ctx)

    if view_dto and container.view_sender:
        await container.view_sender.send(view_dto)
