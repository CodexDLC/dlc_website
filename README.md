# dlc_website

> Django + Telegram Bot project.

## Quick Start

```bash
# Install dependencies
poetry install

# Run
# Django dev server
cd src/backend_django
python manage.py runserver

# Telegram Bot
cd src/telegram_bot
python -m main

# Docker
cd deploy
docker compose up -d --build
```

## Structure

```
src/
├── backend_django/   # Django backend
├── telegram_bot/     # Telegram Bot
└── shared/           # Shared utilities
```

## Development

```bash
ruff check src/        # Linting
ruff format src/       # Formatting
mypy src/              # Type checking
pytest                 # Tests
```

## Deploy

Managed via Docker Compose + GitHub Actions CI/CD.

See `deploy/` for Docker configs and `.github/workflows/` for pipelines.
