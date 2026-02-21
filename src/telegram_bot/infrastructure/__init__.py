"""
Database layer for Telegram Bot (Direct mode).
Used when 02_telegram_bot accesses the infrastructure directly instead of through FastAPI API.

Enable this layer when BOT_DATA_MODE=direct in .env.
When BOT_DATA_MODE=api, this package is not used — data flows through API clients.
"""
