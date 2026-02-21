# Project Template

[🇬🇧 English](./README.md)

> **Модульный Monorepo-шаблон**: Django / FastAPI / Telegram Bot — с инсталлятором, Docker, CI/CD и изоляцией схем PostgreSQL.

---

## Быстрый старт

### 1. Клонирование

```bash
# В новую папку:
git clone https://github.com/codexdlc/project-template.git my-project
cd my-project

# Или в текущую папку:
mkdir my-project && cd my-project
git clone https://github.com/codexdlc/project-template.git .
```

### 2. Установка зависимостей

```bash
pip install poetry
poetry config virtualenvs.in-project true
poetry install --all-extras   # ставит всё; инсталлятор потом удалит лишнее
```

### 3. Запуск инсталлятора

```bash
python -m tools.init_project
```

Интерактивный CLI спросит:
- **Имя проекта** — переименовывает конфиги, pyproject.toml и т.д.
- **Бэкенд** — FastAPI, Django или без бэкенда
- **Telegram Bot** — включить или убрать
- **Git init** — создать начальные коммиты

### 4. Что делает инсталлятор

1. **Poetry** — устанавливает зависимости, удаляет ненужные группы (напр. `django` если выбран FastAPI)
2. **Scaffolder** — генерирует `deploy/`, `.github/workflows/`, `.env` из `.tpl` шаблонов
3. **Backend installer** — настраивает выбранный фреймворк (FastAPI готов; Django строится из шаблонов)
4. **Bot installer** — конфигурирует модуль Telegram бота
5. **Cleaner** — удаляет неиспользуемые модули (src, deploy, docs)
6. **Renamer** — заменяет маркер `project-template` на имя вашего проекта
7. **Finalizer** — создаёт два git-коммита: `Install` (полное состояние) → `Activate` (чистый проект)

---

## Структура проекта

```
project-template/
├── src/
│   ├── backend_fastapi/      # FastAPI бэкенд (async, features-based)
│   ├── backend_django/       # Django бэкенд (features-based структура)
│   ├── telegram_bot/         # Telegram Bot (aiogram 3.x)
│   ├── workers/              # Фоновые воркеры (arq)
│   └── shared/               # Общий код: конфиг, логирование, константы
├── tools/
│   ├── init_project/         # Модульный инсталлятор (сохраняется после установки)
│   │   ├── actions/          # Poetry, Docker, Scaffolder, Cleaner, Renamer, Finalizer
│   │   └── installers/       # Инсталлятор для каждого фреймворка + resources/
│   ├── dev/                  # Утилиты разработчика
│   ├── media/                # Медиа-утилиты (конвертация, QR-коды)
│   └── migration_agent.py    # Миграция существующих проектов в этот шаблон
├── deploy/                   # Генерируется: docker-compose, nginx (из .tpl)
├── .github/workflows/        # Генерируется: CI/CD пайплайны (из .tpl)
├── docs/                     # Документация (en_EN / ru_RU)
├── data/                     # Тома, локальные данные (в .gitignore)
└── pyproject.toml            # Poetry, Ruff, Mypy, Pytest конфиги
```

---

## Бэкенды

### FastAPI (async REST API)

- **Архитектура**: Features-based с Clean Architecture слоями внутри каждой фичи
- **База данных**: SQLAlchemy 2.0 (async) + Alembic миграции
- **Конфиг**: Pydantic Settings v2, `.env` файл
- **Ключевые фичи**: JWT auth, async PostgreSQL (asyncpg), Pydantic v2 схемы

```
src/backend_fastapi/
├── core/                 # Конфиг, база данных, безопасность, логгер
├── database/
│   ├── models/           # SQLAlchemy модели
│   └── migrations/       # Alembic (env.py, versions/)
├── features/
│   ├── users/            # Auth: JWT, регистрация, логин
│   └── media/            # Загрузка и управление медиафайлами
└── main.py               # Точка входа, регистрация роутеров
```

### Django (full-stack)

- **Архитектура**: На основе features (не плоские apps)
- **Настройки**: Разделены на `base.py` / `dev.py` / `prod.py`
- **Ключевые фичи**: Django Admin, ORM, split settings, изоляция features

```
src/backend_django/
├── core/                 # Ядро проекта (urls, wsgi, asgi)
│   └── settings/         # base.py, dev.py, prod.py
├── features/
│   ├── main/             # Основная feature (views/, selectors/, urls)
│   └── system/           # Системные модели (миксины, базовые модели)
├── static/               # CSS, JS, картинки (отдельно от features)
├── templates/            # Django шаблоны (отдельно от features)
└── locale/               # i18n переводы
```

### Telegram Bot (aiogram 3.x)

- **Фреймворк**: aiogram 3 с паттерном Dispatcher + Router
- **Архитектура**: Фичи разделены по транспорту — `telegram/` (хэндлеры) и `redis/` (асинхронные уведомления)
- **Конфиг**: Pydantic Settings, общий `.env` с FastAPI

```
src/telegram_bot/
├── core/                 # Конфиг, container, factory, routers
├── features/
│   ├── telegram/         # Telegram-фичи (commands, bot_menu)
│   └── redis/            # Redis Stream-фичи (notifications, errors)
├── infrastructure/       # Внешние интеграции
├── middlewares/          # Мидлвари (security, throttling, i18n)
├── resources/            # States, константы, шаблоны
└── services/             # Director, FSM, sender, redis dispatcher
```

### Workers (arq)

- **Фреймворк**: arq (async job queue поверх Redis)
- **Назначение**: Фоновые задачи — уведомления, email, отложенные задания

```
src/workers/
├── core/                 # Базовый воркер, конфиг, email client, рендерер шаблонов
└── notification_worker/  # Задачи уведомлений и точка входа воркера
```

---

## База данных и изоляция схем

Все бэкенды могут использовать **одну базу PostgreSQL** (например Neon) через отдельные схемы:

| Бэкенд   | Схема         | Переменная      |
| :-------- | :------------ | :-------------- |
| FastAPI   | `fastapi_app` | `DB_SCHEMA`     |
| Django    | `django_app`  | `DB_SCHEMA`     |

Каждый бэкенд использует `search_path` для изоляции таблиц:
- **FastAPI**: `connect_args.server_settings.search_path`
- **Django**: `DATABASES.default.OPTIONS.options` (prod.py)

---

## Миграции

Миграции запускаются в **CI/CD пайплайне**, а не при старте приложения (предотвращает race conditions).

### FastAPI (Alembic)

```bash
cd src/backend_fastapi

# Создать миграцию
alembic revision --autogenerate -m "add_users_table"

# Применить
alembic upgrade head

# Docker
docker compose run --rm -T backend alembic upgrade head
```

### Django

```bash
cd src/backend_django

python manage.py makemigrations
python manage.py migrate

# Docker
docker compose run --rm -T backend python manage.py migrate --noinput
```

---

## Конфигурация

### Переменные окружения

- **FastAPI + Bot + Workers** — общий корневой `.env` (загружается через `pydantic-settings`)
- **Django** — свой `src/backend_django/.env` (загружается через `python-dotenv`)

Основные переменные:

| Переменная      | Описание                 | По умолчанию   |
| :-------------- | :----------------------- | :------------- |
| `DATABASE_URL`  | PostgreSQL подключение   | (обязательно)  |
| `DB_SCHEMA`     | Имя схемы                | по бэкенду     |
| `BOT_TOKEN`     | Токен Telegram бота      | (обязательно)  |
| `REDIS_URL`     | Redis для arq воркеров   | (обязательно)  |
| `SECRET_KEY`    | Django/JWT секрет        | (обязательно)  |
| `DEBUG`         | Режим отладки            | `True`         |

### Deploy и CI/CD

Docker и GitHub Actions конфиги **генерируются** инсталлятором из `.tpl` шаблонов:

```
tools/init_project/actions/docker/resources/    → deploy/
tools/init_project/actions/scaffolder/resources/ → .github/workflows/
```

CD пайплайн запускает миграции **перед** `docker compose up -d`.

---

## Инструменты

### Инсталлятор (`tools/init_project/`)

Инсталлятор **сохраняется после установки** — не удаляется. Можно переиспользовать или ссылаться на его шаблоны.

### Добавление модуля (`tools/init_project/add_module.py`)

Восстановить ранее удалённый модуль (например, добавить бота к проекту только с FastAPI):

```bash
python -m tools.init_project.add_module bot       # алиас для telegram_bot
python -m tools.init_project.add_module fastapi
python -m tools.init_project.add_module django
```

Использует `git checkout` из Install-коммита для восстановления src, deploy и docs.

### Удаление модуля (`tools/init_project/remove_module.py`)

Удалить модуль, который больше не нужен:

```bash
python -m tools.init_project.remove_module bot
python -m tools.init_project.remove_module fastapi --no-commit
python -m tools.init_project.remove_module django
```

Удаляет все директории модуля (src, deploy, docs) и создаёт git-коммит. Флаг `--no-commit` — пропустить автокоммит.

### Агент миграции (`tools/migration_agent.py`)

Перенести существующий проект в структуру этого шаблона:

```bash
python tools/migration_agent.py /path/to/existing-project
```

Анализирует проект, создаёт стандартные директории, переносит модули и генерирует TODO-отчёт для ручных шагов.

---

## Разработка

```bash
# Линтинг
ruff check src/
ruff format src/

# Проверка типов
mypy src/

# Тесты
pytest

# Pre-commit хуки
pre-commit install
pre-commit run --all-files
```

Конфиги инструментов в `pyproject.toml` (Ruff, Mypy, Pytest).

---

## Технологический стек

| Компонент   | Технология                                     |
| :---------- | :--------------------------------------------- |
| Python      | 3.13+                                          |
| FastAPI     | FastAPI, SQLAlchemy 2.0, asyncpg, Alembic      |
| Django      | Django 5.1, psycopg2, gunicorn                 |
| Bot         | aiogram 3.x                                    |
| Workers     | arq (async job queue поверх Redis)             |
| БД          | PostgreSQL (совместимо с Neon), изоляция схем   |
| Cache/Queue | Redis                                          |
| Конфиг      | Pydantic Settings v2, python-dotenv (Django)    |
| Сборка      | Poetry (PEP 621)                               |
| Линтинг     | Ruff, Mypy, pre-commit                         |
| CI/CD       | GitHub Actions, Docker Compose                  |

---

Copyright © 2026 CodexDLC. MIT License.
