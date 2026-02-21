"""
SQLAlchemy models for Telegram Bot (Direct mode).
Place your models here when the 02_telegram_bot works directly with the infrastructure.

Import all models here so Alembic can discover them for autogenerate.
"""

from .base import Base, TimestampMixin  # noqa: F401

# Import your models below:
# from .user import BotUser  # noqa: F401
