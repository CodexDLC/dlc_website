"""
Общие обработчики FSM состояний.
Garbage collector - удаляет нежелательные текстовые сообщения в состояниях,
где ожидается только нажатие inline-кнопок.
"""

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger as log

from src.telegram_bot.core.garbage_collector import IsGarbageStateFilter

router = Router(name="common_fsm_router")


@router.message(F.text, IsGarbageStateFilter())
async def delete_garbage_text(m: Message, state: FSMContext):
    """
    Удаляет нежелательные текстовые сообщения в состояниях,
    где ожидается нажатие на inline-кнопку.
    Стейты определяются динамически через GarbageStateRegistry.
    """
    user_id = m.from_user.id if m.from_user else "N/A"
    current_state = await state.get_state()

    log.info(f"Garbage collector triggered for user {user_id} in state {current_state}")

    try:
        await m.delete()
        text_preview = m.text[:20] if m.text else ""
        log.debug(f"GarbageMessage | status=deleted user_id={user_id} text='{text_preview}'")
    except TelegramAPIError as e:
        log.warning(f"GarbageMessage | status=delete_failed user_id={user_id} error='{e}'")
