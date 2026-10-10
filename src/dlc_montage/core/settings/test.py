"""
Test settings — used only for pytest.

Inherits from base settings but uses SQLite in-memory for speed.
"""

from .base import *  # noqa: F403

# Enable debug mode in tests for detailed error pages
DEBUG = True
LOG_FILE_ENABLED = False
LOG_LEVEL_CONSOLE = "WARNING"

# SQLite in-memory database for fast tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# In-memory cache for tests (no Redis)
import os

import dj_database_url
from cryptography.fernet import Fernet

# A clean checkout needs no working-data encryption key to run isolated tests.
FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY") or Fernet.generate_key().decode("ascii")

# Explicit opt-in to a dedicated integration database. Never implicitly use the application DB.
if os.environ.get("TEST_DATABASE_URL"):
    DATABASES = {"default": dj_database_url.parse(os.environ["TEST_DATABASE_URL"], conn_max_age=600)}
    if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
        raise ValueError("TEST_DATABASE_URL must point to dedicated PostgreSQL.")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Disable Redis password for tests
REDIS_PASSWORD = None
CODEX_REDIS_ENABLED = False

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable migrations for speed (optional)
# MIGRATION_MODULES = {app: None for app in INSTALLED_APPS}

# Fast password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
