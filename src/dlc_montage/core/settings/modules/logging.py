import os
from pathlib import Path

# Root of Django project: src/backend_django
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# ═══════════════════════════════════════════
# Logging (codex-core compatible)
# ═══════════════════════════════════════════

# Loguru / codex-core compatible fields (used in core/logger.py)
LOG_LEVEL_CONSOLE = os.environ.get("LOG_LEVEL_CONSOLE", "INFO")
LOG_LEVEL_FILE = os.environ.get("LOG_LEVEL_FILE", "DEBUG")
LOG_ROTATION = os.environ.get("LOG_ROTATION", "10 MB")
LOG_DIR = os.environ.get("LOG_DIR", str(BASE_DIR.parent.parent / "logs"))
LOG_FILE_ENABLED = os.environ.get("LOG_FILE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

# Standard Django LOGGING (fallback if loguru is disabled/missing)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL_CONSOLE,
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}
