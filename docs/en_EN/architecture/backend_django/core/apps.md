# 📜 Application Configuration (`apps.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `apps.py` file defines the configuration for the `core` Django application. It includes the `AppConfig` class, which is used to configure application-specific metadata and to perform actions when Django starts up, such as initializing logging.

## `CoreConfig` Class

The `CoreConfig` class inherits from `django.apps.AppConfig` and provides a place for application-specific configurations and startup logic.

### Attributes

*   `default_auto_field = "django.db.models.BigAutoField"`:
    Specifies the type of `AutoField` to use for models by default. `BigAutoField` is a 64-bit integer, which is suitable for most applications.
*   `name = "core"`:
    Defines the full Python path to the application (in this case, `core`).

### `ready()` Method

```python
def ready(self):
    """
    Initialize Loguru logging when Django starts.
    Ensures it runs only once.
    """
    if not getattr(settings, "LOGURU_SETUP", False):
        from .logger import setup_logging

        setup_logging(
            base_dir=settings.BASE_DIR,
            config={
                "LOG_LEVEL_CONSOLE": getattr(settings, "LOG_LEVEL_CONSOLE", "INFO"),
                "LOG_LEVEL_FILE": getattr(settings, "LOG_LEVEL_FILE", "DEBUG"),
                "LOG_ROTATION": getattr(settings, "LOG_ROTATION", "10 MB"),
                "DEBUG": settings.DEBUG,
            },
        )
        # Mark as setup to prevent double initialization
        settings.LOGURU_SETUP = True
```

### Description

The `ready()` method is called by Django when the application is ready. It is used here to initialize the Loguru logging system for the entire Django project.

### Process

1.  **Logging Initialization Check:** It checks for a custom `LOGURU_SETUP` attribute on Django's `settings` object. This ensures that the logging setup function is called only once, even if `ready()` is triggered multiple times (e.g., during tests or by different processes).
2.  **Import `setup_logging`:** Dynamically imports the `setup_logging` function from the local `logger.py` module.
3.  **Call `setup_logging`:** Invokes `setup_logging`, passing:
    *   `base_dir`: The project's base directory from Django settings.
    *   `config`: A dictionary of logging-related settings (console level, file level, rotation, debug mode), retrieved from Django settings.
4.  **Mark as Setup:** Sets `settings.LOGURU_SETUP = True` to prevent subsequent calls to `ready()` from re-initializing Loguru.

## Usage

This `apps.py` configuration is automatically discovered by Django when `core` is included in `INSTALLED_APPS`. The `ready()` method ensures that the logging system is properly configured as soon as the application starts.
