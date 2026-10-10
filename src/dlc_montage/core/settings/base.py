"""
Cloud-Native Django Settings.
Supports layered configuration: Environment Variables > Project .env > Common .env.
Ready for Docker Compose, Swarm, and Kubernetes.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ═══════════════════════════════════════════
# Paths & Project Identity
# ═══════════════════════════════════════════

# Root of Django project (where manage.py is)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 1. Try to load Common .env (Infrastructure level)
# Path can be overridden via ENV_COMMON_PATH for Swarm/K8s
common_env = os.environ.get("ENV_COMMON_PATH")
if common_env and os.path.exists(common_env):
    load_dotenv(common_env, override=False)
else:
    # Fallback for local dev: look 2 levels up
    load_dotenv(BASE_DIR.parent.parent / ".env", override=False)

# 2. Try to load Project-specific .env
# override=False ensures container/orchestrator environment variables take precedence
project_env = os.environ.get("ENV_PROJECT_PATH")
if project_env and os.path.exists(project_env):
    load_dotenv(project_env, override=False)
else:
    # Fallback for local dev: look in current folder
    load_dotenv(BASE_DIR / ".env", override=False)

# 3. Project Identity
# Must be set in .env or by Orchestrator. Fallback to folder name.
PROJECT_NAME = os.environ.get("PROJECT_NAME", BASE_DIR.name)

# ═══════════════════════════════════════════
# Core Django Settings (MUST be defined early)
# ═══════════════════════════════════════════
ROOT_URLCONF = "dlc_montage.core.urls"
WSGI_APPLICATION = "dlc_montage.core.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ═══════════════════════════════════════════
# Import Modules
# ═══════════════════════════════════════════

from .modules.security import *  # noqa
from .modules.apps import *  # noqa
from .modules.middleware import *  # noqa
from .modules.database import *  # noqa
from .modules.cache import *  # noqa
from .modules.internationalization import *  # noqa
from .modules.static import *  # noqa
from .modules.templates import *  # noqa
from .modules.logging import *  # noqa
from .modules.admin import *  # noqa
from .modules.sitemap import *  # noqa
from .modules.codex import *  # noqa
from .modules.private_storage import *  # noqa

# ═══════════════════════════════════════════
# General Settings
# ═══════════════════════════════════════════
# Nextcloud WebDAV Integration (MBG Cloud)
NEXTCLOUD_WEBDAV_URL = os.environ.get("NEXTCLOUD_WEBDAV_URL", "")
NEXTCLOUD_USER = os.environ.get("NEXTCLOUD_USER", "")
NEXTCLOUD_PASSWORD = os.environ.get("NEXTCLOUD_PASSWORD", "")
