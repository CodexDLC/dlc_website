import os
from pathlib import Path

# Root of Django project: src/backend_django
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
_PROJECT_NAME = os.environ.get("PROJECT_NAME", BASE_DIR.name)

# ═══════════════════════════════════════════
# Static & Media
# ═══════════════════════════════════════════

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static", BASE_DIR / "cabinet" / "static"]

# In Docker, static files are collected into a subdirectory named after the project
if os.environ.get("IS_DOCKER", "False").lower() in ("true", "1", "t"):
    STATIC_ROOT = Path("/app/staticfiles") / _PROJECT_NAME
    MEDIA_ROOT = Path("/app/media") / _PROJECT_NAME
else:
    STATIC_ROOT = BASE_DIR / "staticfiles"
    MEDIA_ROOT = BASE_DIR / "media"

# We ignore source CSS files that are compiled into app.css
STATICFILES_IGNORE_PATTERNS = [
    "css/base/*",
    "css/adaptive/*",
    "css/components/*",
    "css/cabinet/*",
    "css/pages/*",
    "css/base.css",
    "css/cabinet.css",
]

MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
