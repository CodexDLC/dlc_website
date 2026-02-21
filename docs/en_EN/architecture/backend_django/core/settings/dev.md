# 📜 Development Settings (`dev.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This `dev.py` file contains Django settings specifically tailored for the local development environment. It inherits all configurations from `base.py` and then overrides or extends them to enable debugging tools, use a local database (SQLite), and provide more verbose logging.

## Purpose

The `dev.py` settings facilitate a productive development workflow by:
*   Enabling Django's debug mode.
*   Integrating the Django Debug Toolbar.
*   Ensuring that development-friendly database configurations are used.
*   Providing detailed logging to the console.

## Sections

### Inheritance

```python
from .base import *  # noqa: F401,F403
```
This line imports all settings from `base.py`, making them available in `dev.py`. This ensures that common configurations are inherited, and only development-specific settings need to be defined or overridden.

### Debug

*   `DEBUG = True`: Explicitly sets Django's debug mode to `True`, which enables detailed error pages, disables template caching, and allows for other development-time conveniences.
*   `INSTALLED_APPS += ["debug_toolbar"]`: Adds the `debug_toolbar` application to `INSTALLED_APPS`, integrating the Django Debug Toolbar for performance profiling and debugging.
*   `MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]`: Adds the `DebugToolbarMiddleware` to the middleware stack, enabling the Debug Toolbar's functionality.
*   `INTERNAL_IPS = ["127.0.0.1"]`: Specifies the IP addresses that are considered "internal" for the Debug Toolbar, allowing it to display only for requests originating from these IPs.

### Database — SQLite

The `dev.py` file does not explicitly configure the database because `base.py` already sets up SQLite as the default if `DATABASE_URL` is not provided in the environment. This means local development typically uses SQLite without further configuration here.

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
        "level": "DEBUG",
    },
}
```
This section overrides the default logging configuration to provide more verbose output to the console during development.
*   `version: 1`: Specifies the logging configuration schema version.
*   `disable_existing_loggers: False`: Ensures that existing loggers are not disabled.
*   `handlers`: Defines a `console` handler that outputs log messages to `sys.stderr`.
*   `root`: Configures the root logger to use the `console` handler and sets the logging level to `DEBUG`, meaning all messages from `DEBUG` level and above will be displayed.
