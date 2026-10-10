"""
dlc_montage — Development Settings.

Inherits from base.py. SQLite, DEBUG=True, verbose logging.
"""

from .base import *  # noqa: F403

# ═══════════════════════════════════════════
# Debug
# ═══════════════════════════════════════════

DEBUG = True

# Development uses the explicitly configured key, including for existing encrypted data.

# ═══════════════════════════════════════════
# Cache — LocMemCache (no Redis needed in dev)
# ═══════════════════════════════════════════

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ═══════════════════════════════════════════
# CSRF Trusted Origins
# ═══════════════════════════════════════════

CSRF_TRUSTED_ORIGINS = ["http://localhost:8080"]

# ═══════════════════════════════════════════
# Database — SQLite
# ═══════════════════════════════════════════

# SQLite is already configured in base.py as default.
# No changes needed here unless you want to override.

# ═══════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════

# In dev, we might want more verbose logging to console
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
        "level": "DEBUG",
    },
}
