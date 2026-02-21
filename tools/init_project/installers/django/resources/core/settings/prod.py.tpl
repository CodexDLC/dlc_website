"""
{{PROJECT_NAME}} — Production Settings.

Inherits from base.py. Postgres, DEBUG=False, security hardened.
"""

import os

from .base import *  # noqa: F401,F403

# ═══════════════════════════════════════════
# Security
# ═══════════════════════════════════════════

DEBUG = False

# HTTPS
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ═══════════════════════════════════════════
# Database — PostgreSQL
# ═══════════════════════════════════════════

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "{{PROJECT_NAME}}"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "postgres"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "OPTIONS": {
            # Schema isolation: Django only sees django_app + public schemas.
            # Migrations create tables in django_app schema.
            # This allows sharing one DB (e.g. Neon) with FastAPI/Bot
            # without table name conflicts.
            "options": f"-c search_path={os.environ.get('DB_SCHEMA', 'django_app')},public",
        },
    }
}

# ═══════════════════════════════════════════
# Static files — collected by collectstatic
# ═══════════════════════════════════════════

STATIC_ROOT = BASE_DIR / "staticfiles"

# ═══════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}
