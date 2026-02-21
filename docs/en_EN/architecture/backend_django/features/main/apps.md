# 📜 Application Configuration (`apps.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This `apps.py` file defines the configuration for the `main` Django application (feature). It includes basic metadata about the application, such as its name and verbose name.

## `MainConfig` Class

The `MainConfig` class inherits from `django.apps.AppConfig` and provides a place for application-specific configurations.

### Attributes

*   `default_auto_field = "django.db.models.BigAutoField"`:
    Specifies the type of `AutoField` to use for models by default. `BigAutoField` is a 64-bit integer, which is suitable for most applications.
*   `name = "features.main"`:
    Defines the full Python path to the application. This is important for Django to correctly locate the app's modules (models, views, etc.) within the `features` directory.
*   `verbose_name = "Main"`:
    Provides a human-readable name for the application, which is often used in the Django Admin interface.

## Usage

This `apps.py` configuration is automatically discovered by Django when `features.main` is included in `INSTALLED_APPS` in the project's settings. It helps Django understand the structure and purpose of the `main` application.
