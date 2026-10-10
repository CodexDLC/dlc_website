import os
from pathlib import Path

from codex_django.core.i18n.discovery import discover_locale_paths

# Root of Django project: src/backend_django
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# ═══════════════════════════════════════════
# Internationalization
# ═══════════════════════════════════════════

LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", "ru")
TIME_ZONE = os.environ.get("TIME_ZONE", "Europe/Berlin")
USE_I18N = True
USE_TZ = True
LANGUAGES = [
    ("ru", "Russian"),
    ("de", "Deutsch"),
]

try:
    import modeltranslation  # noqa

    MODELTRANSLATION_DEFAULT_LANGUAGE = LANGUAGE_CODE.split("-")[0]
    MODELTRANSLATION_LANGUAGES = ("ru", "de", )
except ImportError:
    pass

LOCALE_PATHS = discover_locale_paths(BASE_DIR)
LOCALE_PATHS = [BASE_DIR / "locale", *LOCALE_PATHS]
