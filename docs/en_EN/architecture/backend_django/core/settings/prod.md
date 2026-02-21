# 📜 Production Settings (`prod.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This `prod.py` file contains Django settings specifically tailored for the production deployment environment. It inherits all configurations from `base.py` and then overrides or extends them to enhance security, optimize static file serving, and configure logging for a production context.

## Purpose

The `prod.py` settings ensure that the Django application is secure, performant, and correctly configured for a live environment by:
*   Disabling debug mode by default.
*   Enabling HTTPS-related security measures.
*   Specifying the correct static file root for Nginx.
*   Configuring production-appropriate logging levels.

## Sections

### Inheritance

```python
from .base import *  # noqa: F401,F403
```
This line imports all settings from `base.py`, making them available in `prod.py`. This ensures that common configurations are inherited, and only production-specific settings need to be defined or overridden.

### Security

*   `DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")`:
    Overrides the `DEBUG` setting. By default, `DEBUG` is `False` in production for security reasons, but it can still be explicitly enabled via an environment variable for specific debugging needs.
*   **HTTPS Settings:**
    ```python
    if not DEBUG:
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
        SECURE_SSL_REDIRECT = True
        SECURE_HSTS_SECONDS = 31_536_000  # 1 year
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
    ```
    This block enables various HTTPS-related security settings when `DEBUG` is `False`:
    *   `SECURE_PROXY_SSL_HEADER`: Tells Django that the application is behind an SSL-terminating proxy (like Nginx) and to trust the `X-Forwarded-Proto` header.
    *   `SECURE_SSL_REDIRECT`: Redirects all non-HTTPS requests to HTTPS.
    *   `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`: Configures HTTP Strict Transport Security (HSTS) to force browsers to interact with the site only over HTTPS.
    *   `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`: Ensures that session and CSRF cookies are only sent over HTTPS connections.

### Static Files

*   `STATIC_ROOT = BASE_DIR / "staticfiles"`:
    Explicitly sets `STATIC_ROOT` to `BASE_DIR / "staticfiles"`. This is the absolute path to the directory where Django's `collectstatic` command will gather all static files for serving by Nginx in production.

### Logging

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}
```
This section configures logging for production.
*   `root` logger `level` is set to `WARNING`, meaning only `WARNING` level messages and above will be output to the console. This reduces log verbosity in production compared to development.
