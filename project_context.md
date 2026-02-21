# Project Context: Architecture & Integration Plan

## 1. Текущая архитектура (Architecture Overview)
*   **Shared Core (`src/shared`):** Общая логика, логгер, базовые настройки (`pydantic-settings`), работа с Redis.
*   **Telegram Bot (`src/telegram_bot`):** Бот на `aiogram 3.x`. Поддерживает режимы `api` (через бэкенд) и `direct` (своя БД).
*   **Workers (`src/workers`):** Фоновые задачи на `arq`. Основной воркер — `notification_worker`.
*   **Backend Django (`src/backend_django`):** Бэкенд на Django с использованием `django-ninja`.
*   **Init System (`tools/init_project`):** Оркестратор для развертывания шаблона.

## 2. Технические стандарты Docker
*   **Multi-stage builds:** Использование `python:3.13-slim` и `builder` стадии с `poetry export`.
*   **Django:** Обязательный `entrypoint.sh` для автоматического выполнения `migrate` и `collectstatic`.
*   **Worker:** Запуск через `arq src.workers.notification_worker.worker.WorkerSettings`.
*   **Compose:** Секционная сборка (отдельно db, redis, backend, bot, worker, nginx).

## 3. План реализации (Execution Plan)

### Этап 1: Конфигурация (Environment)
1.  Создать `tools/init_project/actions/docker/resources/env.tpl` со всеми переменными:
    *   Блок PostgreSQL (DB, User, Password, Host, Port).
    *   Блок Redis (Host, Port).
    *   Блок Telegram Bot (Token, Mode, Admin IDs, Topics).
    *   Блок Backend API (URL, Key).
    *   Блок Django (Secret Key, Allowed Hosts).
    *   Блок Docker Images (Backend, Bot, Worker, Nginx).

### Этап 2: Docker-шаблоны (Templates)
1.  **Django Dockerfile:** Обновить на multi-stage с `poetry export`.
2.  **Worker Dockerfile:** Обновить на multi-stage, исправить пути на `src/workers` и `src/shared`.
3.  **Entrypoint:** Создать `tools/init_project/actions/docker/resources/django/entrypoint.sh.tpl`.

### Этап 3: Логика инсталлятора (Actions)
1.  **DockerAction.py:**
    *   Добавить рендеринг `entrypoint.sh`.
    *   Добавить копирование `scripts/init_db_schemas.sql` в `deploy/`.
    *   Синхронизировать имена контейнеров в `docker-compose.yml` (префикс проекта).
2.  **BotInstaller.py:**
    *   Добавить создание папок `logs/bot`, `logs/worker`.
3.  **CleanerAction.py:**
    *   Убедиться, что `src/workers` удаляется вместе с ботом.

### Этап 4: Зависимости (Poetry)
1.  **PoetryAction.py:**
    *   Настроить установку с учетом extras: `poetry install --with bot,django,shared`.

## 4. Переменные окружения (Reference)
Используется единый `.env` в корне для Docker Compose и бота. Django может использовать свой `.env` в `src/backend_django/` или общий.
