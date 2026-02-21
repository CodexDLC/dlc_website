"""
{{PROJECT_NAME}} — Development Settings.

Inherits from base.py. SQLite, DEBUG=True, verbose logging.
"""

from .base import *  # noqa: F401,F403

# ═══════════════════════════════════════════
# Development overrides
# ═══════════════════════════════════════════

DEBUG = True

# SQLite for dev (already default in base.py)
# Override DATABASE if needed:
# DATABASES["default"] = {
#     "ENGINE": "django.db.backends.sqlite3",
#     "NAME": BASE_DIR / "db.sqlite3",
# }

# ═══════════════════════════════════════════
# Debug tools (add django-debug-toolbar here)
# ═══════════════════════════════════════════

# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
# INTERNAL_IPS = ["127.0.0.1"]
