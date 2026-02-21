# Project Template

[🇷🇺 Русский](./README-RU.md)

> **Modular Monorepo Template**: Django / FastAPI / Telegram Bot — with installer, Docker, CI/CD, and PostgreSQL schema isolation.

---

## Quick Start

### 1. Clone

```bash
# Into a new folder:
git clone https://github.com/codexdlc/project-template.git my-project
cd my-project

# Or into the current folder:
mkdir my-project && cd my-project
git clone https://github.com/codexdlc/project-template.git .
```

### 2. Install dependencies

```bash
pip install poetry
poetry config virtualenvs.in-project true
poetry install --all-extras   # installs everything; installer will clean up unused
```

### 3. Run the installer

```bash
python -m tools.init_project
```

The interactive CLI will ask:
- **Project name** — renames configs, pyproject.toml, etc.
- **Backend** — FastAPI, Django, or none
- **Telegram Bot** — include or remove
- **Git init** — create initial commits

### 4. What the installer does

1. **Poetry** — installs dependencies, removes unused groups (e.g. `django` group if FastAPI was chosen)
2. **Scaffolder** — generates `deploy/`, `.github/workflows/`, `.env` from `.tpl` templates
3. **Backend installer** — sets up the chosen framework (FastAPI is ready; Django is built from templates)
4. **Bot installer** — configures the Telegram bot module
5. **Cleaner** — removes unused modules (src dirs, deploy dirs, docs)
6. **Renamer** — replaces `project-template` marker with your project name
7. **Finalizer** — creates two git commits: `Install` (full state) → `Activate` (clean project)

---

## Project Structure

```
project-template/
├── src/
│   ├── backend_fastapi/      # FastAPI backend (async, features-based)
│   ├── backend_django/       # Django backend (features-based structure)
│   ├── telegram_bot/         # Telegram Bot (aiogram 3.x)
│   ├── workers/              # Background workers (arq)
│   └── shared/               # Shared code: config, logging, constants
├── tools/
│   ├── init_project/         # Modular installer (kept after install)
│   │   ├── actions/          # Poetry, Docker, Scaffolder, Cleaner, Renamer, Finalizer
│   │   └── installers/       # Per-framework installers + resources/
│   ├── dev/                  # Developer utilities
│   ├── media/                # Media utilities (convert, QR)
│   └── migration_agent.py    # Migrate existing projects to this template
├── deploy/                   # Generated: docker-compose, nginx (from .tpl)
├── .github/workflows/        # Generated: CI/CD pipelines (from .tpl)
├── docs/                     # Documentation (en_EN / ru_RU)
├── data/                     # Volumes, local data (gitignored)
└── pyproject.toml            # Poetry, Ruff, Mypy, Pytest configs
```

---

## Backends

### FastAPI (async REST API)

- **Architecture**: Features-based with Clean Architecture layers per feature
- **Database**: SQLAlchemy 2.0 (async) + Alembic migrations
- **Config**: Pydantic Settings v2, `.env` file
- **Key features**: JWT auth, async PostgreSQL (asyncpg), Pydantic v2 schemas

```
src/backend_fastapi/
├── core/                 # Config, database, security, logger
├── database/
│   ├── models/           # SQLAlchemy models
│   └── migrations/       # Alembic (env.py, versions/)
├── features/
│   ├── users/            # Auth: JWT, registration, login
│   └── media/            # Media upload/management
└── main.py               # App entrypoint, router registration
```

### Django (full-stack)

- **Architecture**: Features-based (not flat apps)
- **Settings**: Split into `base.py` / `dev.py` / `prod.py`
- **Key features**: Django Admin, ORM, split settings, feature isolation

```
src/backend_django/
├── core/                 # Project core (urls, wsgi, asgi)
│   └── settings/         # base.py, dev.py, prod.py
├── features/
│   ├── main/             # Main feature (views/, selectors/, urls)
│   └── system/           # System models (mixins, base models)
├── static/               # CSS, JS, images (separate from features)
├── templates/            # Django templates (separate from features)
└── locale/               # i18n translations
```

### Telegram Bot (aiogram 3.x)

- **Framework**: aiogram 3 with Dispatcher + Router pattern
- **Architecture**: Features split by transport — `telegram/` (handlers) and `redis/` (async notifications)
- **Config**: Pydantic Settings, shared `.env` with FastAPI

```
src/telegram_bot/
├── core/                 # Config, container, factory, routers
├── features/
│   ├── telegram/         # Telegram-driven features (commands, bot_menu)
│   └── redis/            # Redis Stream-driven features (notifications, errors)
├── infrastructure/       # External integrations
├── middlewares/          # Aiogram middlewares (security, throttling, i18n)
├── resources/            # States, constants, templates
└── services/             # Director, FSM, sender, redis dispatcher
```

### Workers (arq)

- **Framework**: arq (async job queue over Redis)
- **Purpose**: Background tasks — notifications, emails, scheduled jobs

```
src/workers/
├── core/                 # Base worker, config, email client, template renderer
└── notification_worker/  # Notification tasks and worker entrypoint
```

---

## Database & Schema Isolation

All backends can share **one PostgreSQL database** (e.g. Neon) using separate schemas:

| Backend  | Schema        | Config variable |
| :------- | :------------ | :-------------- |
| FastAPI  | `fastapi_app` | `DB_SCHEMA`     |
| Django   | `django_app`  | `DB_SCHEMA`     |

Each backend uses `search_path` to isolate tables:
- **FastAPI**: `connect_args.server_settings.search_path`
- **Django**: `DATABASES.default.OPTIONS.options` (prod.py)

---

## Migrations

Migrations run in **CI/CD pipeline**, not at application startup (prevents race conditions).

### FastAPI (Alembic)

```bash
cd src/backend_fastapi

# Create migration
alembic revision --autogenerate -m "add_users_table"

# Apply
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

## Configuration

### Environment Variables

- **FastAPI + Bot + Workers** — shared root `.env` (loaded via `pydantic-settings`)
- **Django** — own `src/backend_django/.env` (loaded via `python-dotenv`)

Key variables:

| Variable        | Description              | Default        |
| :-------------- | :----------------------- | :------------- |
| `DATABASE_URL`  | PostgreSQL connection    | (required)     |
| `DB_SCHEMA`     | Schema name              | per-backend    |
| `BOT_TOKEN`     | Telegram bot token       | (required)     |
| `REDIS_URL`     | Redis for arq workers    | (required)     |
| `SECRET_KEY`    | Django/JWT secret        | (required)     |
| `DEBUG`         | Debug mode               | `True`         |

### Deploy & CI/CD

Docker and GitHub Actions configs are **generated** by the installer from `.tpl` templates:

```
tools/init_project/actions/docker/resources/    → deploy/
tools/init_project/actions/scaffolder/resources/ → .github/workflows/
```

The CD pipeline runs migrations **before** `docker compose up -d`.

---

## Tools

### Installer (`tools/init_project/`)

The installer is **kept after installation** — not deleted. You can re-use it or reference its templates.

### Add Module (`tools/init_project/add_module.py`)

Restore a previously removed module (e.g. add bot to a FastAPI-only project):

```bash
python -m tools.init_project.add_module bot       # alias for telegram_bot
python -m tools.init_project.add_module fastapi
python -m tools.init_project.add_module django
```

Uses `git checkout` from the Install commit to restore src, deploy, and docs.

### Remove Module (`tools/init_project/remove_module.py`)

Remove a module you no longer need:

```bash
python -m tools.init_project.remove_module bot
python -m tools.init_project.remove_module fastapi --no-commit
python -m tools.init_project.remove_module django
```

Deletes all module directories (src, deploy, docs) and creates a git commit. Use `--no-commit` to skip the auto-commit.

### Migration Agent (`tools/migration_agent.py`)

Migrate an existing project to this template structure:

```bash
python tools/migration_agent.py /path/to/existing-project
```

Analyzes your project, creates standard directories, transfers modules, and generates a TODO report for manual steps.

---

## Development

```bash
# Linting
ruff check src/
ruff format src/

# Type checking
mypy src/

# Tests
pytest

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

Tool configs are in `pyproject.toml` (Ruff, Mypy, Pytest).

---

## Tech Stack

| Component  | Technology                                     |
| :--------- | :--------------------------------------------- |
| Python     | 3.13+                                          |
| FastAPI    | FastAPI, SQLAlchemy 2.0, asyncpg, Alembic      |
| Django     | Django 5.1, psycopg2, gunicorn                 |
| Bot        | aiogram 3.x                                    |
| Workers    | arq (async job queue over Redis)               |
| Database   | PostgreSQL (Neon-compatible), schema isolation  |
| Cache/Queue| Redis                                          |
| Config     | Pydantic Settings v2, python-dotenv (Django)    |
| Build      | Poetry (PEP 621)                               |
| Linting    | Ruff, Mypy, pre-commit                         |
| CI/CD      | GitHub Actions, Docker Compose                  |

---

Copyright © 2026 CodexDLC. MIT License.
