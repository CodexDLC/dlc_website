"""
dlc_montage — Production Settings.

Inherits from base.py. Postgres, DEBUG=False strictly enforced, security hardened.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

# ═══════════════════════════════════════════
# Database (PostgreSQL required)
# ═══════════════════════════════════════════

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL environment variable is required in production.")

db_config = dj_database_url.parse(DATABASE_URL)
if db_config.get("ENGINE") != "django.db.backends.postgresql":
    raise ImproperlyConfigured(
        f"Production requires PostgreSQL; received engine '{db_config.get('ENGINE')}'. "
        "SQLite and non-PostgreSQL databases are rejected."
    )

DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=int(os.environ.get("DB_CONN_MAX_AGE", "600")),
        conn_health_checks=True,
    )
}

# ═══════════════════════════════════════════
# Security & Secret Key
# ═══════════════════════════════════════════

# Production strictly forbids DEBUG=True
if os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes"):
    raise ImproperlyConfigured("DEBUG must be False in production.")
DEBUG = False

# Strict production SECRET_KEY validation: non-empty, non-placeholder, >= 32 chars
SECRET_KEY = os.environ.get("SECRET_KEY")
INSECURE_SECRET_KEYS = {
    "",
    "replace-with-your-django-secret-key",
    "django-insecure",
    "change-me",
}
if not SECRET_KEY or SECRET_KEY in INSECURE_SECRET_KEYS or len(SECRET_KEY) < 32:
    raise ImproperlyConfigured(
        "A secure SECRET_KEY (at least 32 characters, non-placeholder) must be provided in production."
    )

# HTTPS settings (active in production with DEBUG=False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() in ("true", "1", "yes")
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
LANGUAGE_COOKIE_SECURE = True

# Production domain(s) and cookie domains from environment; do not hardcode example.com
raw_trusted_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in raw_trusted_origins.split(",") if o.strip()]

CSRF_COOKIE_DOMAIN = os.environ.get("CSRF_COOKIE_DOMAIN") or None
SESSION_COOKIE_DOMAIN = os.environ.get("SESSION_COOKIE_DOMAIN") or None

# ═══════════════════════════════════════════
# Static files
# ═══════════════════════════════════════════

_container_static = Path("/app/staticfiles")
_container_media = Path("/app/media")
STATIC_ROOT = Path(
    os.environ.get("STATIC_ROOT", _container_static if _container_static.exists() else BASE_DIR / "staticfiles")  # noqa: F405
)
MEDIA_ROOT = Path(
    os.environ.get("MEDIA_ROOT", _container_media if _container_media.exists() else BASE_DIR / "media")  # noqa: F405
)

# Preserve existing storages (including private storage) and add content hash to static files
base_storages = globals().get("STORAGES", {})
STORAGES = {
    **base_storages,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

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
