# 📜 Base Settings (`base.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This `base.py` file contains the common Django settings that are applied across all environments (development, production, testing). It loads environment-specific values from `.env` via `os.environ` and sets up fundamental configurations for paths, security, applications, database, caching, internationalization, static/media files, and logging.

## Purpose

The `base.py` settings file ensures consistency across different deployment environments by defining a baseline configuration. Environment-specific overrides are then handled in `dev.py`, `prod.py`, and `test.py`.

## Sections

### Paths

*   `BASE_DIR`: Defines the project's root directory (`src/backend_django`).
*   `load_dotenv(BASE_DIR.parent.parent / ".env")`: Loads environment variables from the `.env` file located two levels up from `src/backend_django` (i.e., the project root).

### Security

*   `SECRET_KEY`: Django's secret key, loaded from the `SECRET_KEY` environment variable (defaults to an insecure value if not set).
*   `DEBUG`: Boolean flag for debug mode, loaded from the `DEBUG` environment variable.
*   `ALLOWED_HOSTS`: A list of hostnames that Django allows to serve the application. It includes `localhost`, `127.0.0.1`, `backend` by default, and dynamically adds domains from `SITE_BASE_URL` and its `www` subdomain.
*   `SITE_BASE_URL`: The base URL of the site, loaded from the `SITE_BASE_URL` environment variable.

### Application Definition

*   `INSTALLED_APPS`: A list of all Django applications installed in the project, including third-party apps (`django_prometheus`, `modeltranslation`, `django.contrib.*`) and custom feature apps (`core`, `features.main`, `features.system`, `features.booking`, `ninja`).
*   `MIDDLEWARE`: A list of middleware classes that process requests and responses. It includes Django's built-in middleware, `django_prometheus` middleware for metrics, and `django.middleware.locale.LocaleMiddleware` for internationalization.
*   `ROOT_URLCONF`: Specifies the root URL configuration module (`core.urls`).
*   `TEMPLATES`: Configures Django's template engine, specifying template directories and context processors (including `features.system.context_processors.site_settings`).
*   `WSGI_APPLICATION`: Specifies the WSGI application entry point (`core.wsgi.application`).

### Database

*   `DATABASE_URL`: Loads the database connection URL from the `DATABASE_URL` environment variable.
*   `DATABASES`: Configures the `default` database connection. If `DATABASE_URL` is provided, it uses `dj_database_url.config()` for PostgreSQL (with `conn_max_age` and `conn_health_checks`). Otherwise, it defaults to SQLite.

### Auth

*   `AUTH_PASSWORD_VALIDATORS`: Configures Django's password validation rules.

### Redis & ARQ (Task Queue)

*   `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`: Redis connection details, loaded from environment variables.
*   `IS_INSIDE_DOCKER`: Dynamically detects if the application is running inside a Docker container.
*   **Smart Host Detection:** If `REDIS_HOST` is `localhost` and the app is inside Docker, `REDIS_HOST` is changed to `redis` (the Docker service name).
*   `REDIS_URL`: Constructs the full Redis connection URL, including password encoding if `REDIS_PASSWORD` is provided.

### Telegram Bot Settings

*   `SUPERUSER_IDS`: Comma-separated IDs of superusers for the Telegram bot.
*   `OWNER_IDS`: Comma-separated IDs of owners for the Telegram bot.
*   `BOT_API_KEY`: API key for bot authentication.

### Cache & Sessions (Redis)

*   `CACHES`: Configures the default cache backend to use `django_redis.cache.RedisCache` with the constructed `REDIS_URL`.
*   `SESSION_ENGINE`: Sets the session engine to use the cache backend.
*   `SESSION_CACHE_ALIAS`: Specifies the cache alias for sessions.

### Internationalization

*   `LANGUAGE_CODE`, `TIME_ZONE`: Default language and timezone, loaded from environment variables.
*   `USE_I18N`, `USE_TZ`: Enable internationalization and timezone support.
*   `LANGUAGES`: Defines the supported languages for the project.
*   `MODELTRANSLATION_DEFAULT_LANGUAGE`, `MODELTRANSLATION_LANGUAGES`: Settings for `django-modeltranslation`.
*   `LOCALE_PATHS`: Specifies the directory for translation files.

### Static & Media

*   `STATIC_URL`: URL prefix for static files.
*   `STATICFILES_DIRS`: Additional directories where static files are located.
*   `STATIC_ROOT`: The directory where `collectstatic` will gather all static files for deployment.
*   `MEDIA_URL`: URL prefix for media files.
*   `MEDIA_ROOT`: The directory where user-uploaded media files are stored.
*   `DEFAULT_AUTO_FIELD`: Default primary key field type for models.

### Logging (Loguru)

*   `LOGGING_CONFIG`: Set to `None` to allow custom logging configuration (e.g., via Loguru).
*   `LOG_LEVEL_CONSOLE`, `LOG_LEVEL_FILE`, `LOG_ROTATION`: Logging parameters loaded from environment variables.
