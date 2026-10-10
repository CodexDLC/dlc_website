import os
from urllib.parse import urlparse

# ═══════════════════════════════════════════
# Security
# ═══════════════════════════════════════════

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-CHANGE-ME")
FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY", "")

# Main switch for the whole system
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")
TEST_SITE_NOINDEX = os.environ.get("TEST_SITE_NOINDEX", "False").lower() in ("true", "1", "yes")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Smart ALLOWED_HOSTS ---
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "backend"]

env_hosts = os.environ.get("ALLOWED_HOSTS", "")
if env_hosts:
    ALLOWED_HOSTS.extend([h.strip() for h in env_hosts.split(",") if h.strip()])

SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "http://127.0.0.1:8000/")
if not SITE_BASE_URL.endswith("/"):
    SITE_BASE_URL += "/"

# CSRF: include the configured site URL + common local dev ports
CSRF_TRUSTED_ORIGINS = [SITE_BASE_URL.rstrip("/")]
if DEBUG:
    CSRF_TRUSTED_ORIGINS += [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]

# Canonical domain for SEO (no trailing slash)
CANONICAL_DOMAIN = os.environ.get("CANONICAL_DOMAIN", "")
if CANONICAL_DOMAIN.endswith("/"):
    CANONICAL_DOMAIN = CANONICAL_DOMAIN[:-1]

domain = urlparse(SITE_BASE_URL).netloc
if domain:
    clean_domain = domain.split(":")[0]
    if clean_domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(clean_domain)

    if not clean_domain.startswith("www."):
        www_domain = f"www.{clean_domain}"
        if www_domain not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(www_domain)

if DEBUG:
    # Allow local tunnels dynamically to ease development
    ALLOWED_HOSTS.extend([".ngrok-free.app", ".ngrok-free.dev", ".ngrok.io", ".loca.lt"])
