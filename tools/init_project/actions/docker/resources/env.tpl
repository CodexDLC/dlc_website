# ═══════════════════════════════════════════
# {{PROJECT_NAME}} — Root Environment
# ═══════════════════════════════════════════

# === 1. GENERAL ===
# development | production
ENVIRONMENT=production
DEBUG=False
DOMAIN_NAME={{PROJECT_NAME}}.example.com
SITE_BASE_URL=https://{{PROJECT_NAME}}.example.com/

# === 2. DJANGO SETTINGS ===
SECRET_KEY={{DJANGO_SECRET_KEY}}
DJANGO_SETTINGS_MODULE=core.settings.prod
ALLOWED_HOSTS=localhost,127.0.0.1,backend

# === 3. POSTGRESQL ===
POSTGRES_DB={{PROJECT_NAME}}_db
POSTGRES_USER={{PROJECT_NAME}}_user
POSTGRES_PASSWORD={{POSTGRES_PASSWORD}}
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://{{PROJECT_NAME}}_user:{{POSTGRES_PASSWORD}}@postgres:5432/{{PROJECT_NAME}}_db

# === 4. REDIS ===
REDIS_HOST=redis
REDIS_PORT=6379
# REDIS_PASSWORD=
REDIS_URL=redis://redis:6379/0

# === 5. TELEGRAM BOT ===
BOT_TOKEN={{BOT_TOKEN}}

# Bot <-> Backend API
BACKEND_API_URL=http://backend:8000
BACKEND_API_KEY={{BACKEND_API_KEY}}
BOT_API_KEY={{BOT_API_KEY}}

# Roles (comma-separated Telegram IDs)
SUPERUSER_IDS=
OWNER_IDS=

# Notification channel
TELEGRAM_ADMIN_CHANNEL_ID=
TELEGRAM_NOTIFICATION_TOPIC_ID=1
# TELEGRAM_TOPICS={"topic_name": 2}

# === 6. WORKERS & EMAIL (arq) ===
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=True

# === 7. DOCKER IMAGES ===
DOCKER_IMAGE_BACKEND=my-registry/{{PROJECT_NAME}}-backend:1.0.0
DOCKER_IMAGE_BOT=my-registry/{{PROJECT_NAME}}-bot:1.0.0
DOCKER_IMAGE_WORKER=my-registry/{{PROJECT_NAME}}-worker:1.0.0
DOCKER_IMAGE_NGINX=my-registry/{{PROJECT_NAME}}-nginx:1.0.0

# === 8. MONITORING (Grafana Cloud) ===
# GCLOUD_HOSTED_METRICS_URL=
# GCLOUD_HOSTED_METRICS_ID=
# GCLOUD_HOSTED_LOGS_URL=
# GCLOUD_HOSTED_LOGS_ID=
# GCLOUD_RW_API_KEY=

# === 9. LOGGING ===
LOG_LEVEL=INFO
