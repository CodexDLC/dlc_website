from aiogram import Router

from src.telegram_bot.features.telegram.commands.handlers.router import router as commands_router

router = Router(name="commands_feature_router")

router.include_routers(
    commands_router,
)
