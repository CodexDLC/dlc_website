# Telegram Bot

## Обзор

Telegram-бот на базе aiogram 3.x с поддержкой двух режимов работы с данными.

## Технологии

- **aiogram 3.x** — асинхронный фреймворк для Telegram Bot API
- **Handlers** — обработчики команд и сообщений
- **Middlewares** — промежуточные слои обработки

## Режимы работы (BOT_DATA_MODE)

- **api** — бот обращается к данным через REST API бэкенда
- **direct** — бот работает с базой данных напрямую

Режим задаётся переменной окружения `BOT_DATA_MODE`.

## Структура

```
telegram_bot/
├── handlers/
├── middlewares/
├── keyboards/
└── config.py
```

> Подробнее: [EN](../../../en_EN/architecture/telegram_bot/README.md)
