# ═══════════════════════════════════════════
# {{PROJECT_NAME}} — Development Environment
# ═══════════════════════════════════════════

# Django
DJANGO_SETTINGS_MODULE=core.settings.dev
SECRET_KEY=django-insecure-change-me-in-production-{{PROJECT_NAME}}
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (dev: sqlite, prod: postgres)
# DATABASE_URL=postgres://user:pass@localhost:5432/{{PROJECT_NAME}}

# Redis (optional, for cache/celery)
# REDIS_URL=redis://localhost:6379/0

# Internationalization
LANGUAGE_CODE=en-us
TIME_ZONE=UTC
