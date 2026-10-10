import os
from pathlib import Path

import dj_database_url

# Root of Django project: src/backend_django
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
_PROJECT_NAME = os.environ.get("PROJECT_NAME", BASE_DIR.name)

# ═══════════════════════════════════════════
# Database
# ═══════════════════════════════════════════

DATABASE_URL = os.environ.get("DATABASE_URL")
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")
IS_DOCKER = os.environ.get("IS_DOCKER", "False").lower() in ("true", "1", "t")

if DATABASE_URL:
    # Production (Neon or other)
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif IS_DOCKER and DEBUG:
    # Local Postgres in Docker Cluster (infra)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "dlc_montage"),
            "USER": os.environ.get("POSTGRES_USER", "dlc_montage"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "db"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    # Fallback to SQLite for local development without Docker
    data_dir = BASE_DIR.parent.parent / "data" / "db"
    data_dir.mkdir(parents=True, exist_ok=True)

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(data_dir / f"{_PROJECT_NAME}.sqlite3"),
        }
    }
