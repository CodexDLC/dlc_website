# FastAPI Backend

## Обзор

Асинхронный REST API на базе FastAPI, построенный по принципам Clean Architecture.

## Технологический стек

- **FastAPI** — асинхронный веб-фреймворк
- **SQLAlchemy 2.0** — ORM с поддержкой async
- **Alembic** — управление миграциями БД
- **Pydantic** — валидация данных и схемы

## Архитектура

Проект следует Clean Architecture с разделением на слои:

- **API** — эндпоинты и роутеры
- **Service** — бизнес-логика
- **Repository** — доступ к данным

## Быстрый старт

1. Установить зависимости: `poetry install`
2. Применить миграции: `alembic upgrade head`
3. Запустить сервер: `uvicorn app.main:app --reload`

> Подробнее: [EN](../../../en_EN/architecture/backend-fastapi/README.md)
