# ═══════════════════════════════════════════
# {{PROJECT_NAME}} — Root Environment (Example)
# ═══════════════════════════════════════════
# Copy to .env and fill in your values:
#   cp .env.example .env

# === 1. GENERAL ===
# development | production
ENVIRONMENT=development
DEBUG=True
DOMAIN_NAME={{PROJECT_NAME}}.example.com
SITE_BASE_URL=http://localhost:8000/

# === 2. DJANGO SETTINGS ===
SECRET_KEY=your-secret-key-here
DJANGO_SETTINGS_MODULE=core.settings.dev
ALLOWED_HOSTS=localhost,127.0.0.1

# === 3. POSTGRESQL ===
POSTGRES_DB={{PROJECT_NAME}}_db
POSTGRES_USER={{PROJECT_NAME}}_user
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql://{{PROJECT_NAME}}_user:your-password@localhost:5432/{{PROJECT_NAME}}_db

# === 4. REDIS ===
REDIS_HOST=localhost
REDIS_PORT=6379
# REDIS_PASSWORD=
REDIS_URL=redis://localhost:6379/0

# === 5. TELEGRAM BOT ===
BOT_TOKEN=your-telegram-bot-token

# Bot <-> Backend API
BACKEND_API_URL=http://localhost:8000
BACKEND_API_KEY=your-backend-api-key
BOT_API_KEY=your-bot-api-key

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
LOG_LEVEL=DEBUG
