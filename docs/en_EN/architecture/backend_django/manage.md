# 📜 Django Management Script (`manage.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `manage.py` script is Django's command-line utility for performing administrative tasks. It provides a convenient way to interact with your Django project from the terminal, enabling operations like running the development server, managing database migrations, and executing tests.

## Purpose

The `manage.py` script simplifies common development and deployment tasks by encapsulating the necessary environment setup and providing access to Django's built-in management commands.

## Script Breakdown

```python
#!/usr/bin/env python
"""Django management script."""

import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

### `#!/usr/bin/env python`

Shebang line, specifying that the script should be executed with the Python interpreter found in the user's environment.

### `main()` Function

The `main()` function is the entry point for executing Django's administrative tasks.

*   `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")`:
    Sets the `DJANGO_SETTINGS_MODULE` environment variable to `core.settings.dev`. This tells Django which settings file to use for the current execution. In a development environment, `core.settings.dev` is typically used.
*   `try...except ImportError`:
    Attempts to import `execute_from_command_line` from `django.core.management`. If Django is not installed or not accessible, it raises an `ImportError` with a helpful message.
*   `execute_from_command_line(sys.argv)`:
    This is the core function that parses command-line arguments (`sys.argv`) and executes the corresponding Django management command.

### `if __name__ == "__main__":`

Ensures that the `main()` function is called only when the script is executed directly (not when imported as a module).

## Usage

To use `manage.py`, navigate to the `src/backend_django` directory in your terminal and run commands like:

*   **Run the development server:**
    ```bash
    python manage.py runserver
    ```
*   **Apply database migrations:**
    ```bash
    python manage.py migrate
    ```
*   **Create a new app:**
    ```bash
    python manage.py startapp myapp
    ```
*   **Run tests:**
    ```bash
    python manage.py test
    ```
*   **Create a superuser:**
    ```bash
    python manage.py createsuperuser
    ```
