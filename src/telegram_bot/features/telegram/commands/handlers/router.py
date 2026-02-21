from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.telegram_bot.core.container import BotContainer

router = Router(name="commands_router")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, container: BotContainer):
    """Обработка команды /start."""
    if not message.from_user:
        return

    orchestrator = container.features.get("commands")
    if not orchestrator:
        return

    # 1. Вызываем логику входа
    view_dto = await orchestrator.handle_entry(message.from_user.id, payload=message.from_user)

    # 2. Указываем ID сообщения-команды для удаления
    view_dto.trigger_message_id = message.message_id

    # 3. Отправляем через централизованный сендер
    if container.view_sender:
        await container.view_sender.send(view_dto)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, container: BotContainer):
    """Обработка команды /menu."""
    if not message.from_user:
        return

    orchestrator = container.features.get("bot_menu")
    if not orchestrator:
        return

    # 1. Вызываем логику входа
    view_dto = await orchestrator.handle_entry(message.from_user.id)

    # 2. Указываем ID сообщения-команды для удаления
    view_dto.trigger_message_id = message.message_id

    if container.view_sender:
        await container.view_sender.send(view_dto)
