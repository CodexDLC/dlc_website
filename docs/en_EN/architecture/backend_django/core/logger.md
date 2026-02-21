# 📜 Logging Configuration (`logger.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `logger.py` module provides a centralized and robust logging solution for the Django backend application, leveraging `Loguru` for enhanced logging capabilities. It configures various log sinks (console, debug file, error JSON file) and intercepts standard Python `logging` messages to redirect them to `Loguru`.

## Purpose

The module aims to:
*   Provide clear and colorized console output for development.
*   Store detailed debug logs in a file with rotation and compression.
*   Output structured JSON error logs for easy parsing by monitoring systems.
*   Ensure all logging (including Django's internal logging) is routed through Loguru for consistency.

## `log` Alias

```python
from loguru import logger

log = logger
```
An alias `log` is created for the `logger` instance from `Loguru` for convenience.

## `InterceptHandler` Class

```python
class InterceptHandler(logging.Handler):
    """
    Перехватывает стандартные сообщения `logging` и направляет их в `loguru`.
    """
    def emit(self, record: logging.LogRecord) -> None:
        # ... implementation ...
```

### Description

This custom `logging.Handler` subclass intercepts messages from Python's standard `logging` module and redirects them to `Loguru`. This is crucial for ensuring that logs from Django's internal components and third-party libraries (which typically use `logging`) are processed by Loguru's configured sinks.

### `emit()` Method

The `emit()` method is overridden to:
1.  Determine the appropriate Loguru level from the standard `logging` record.
2.  Adjust the call depth to correctly attribute the log message to its original source.
3.  Call `logger.opt().log()` to pass the message to Loguru.

## `setup_logging()` Function

```python
def setup_logging(base_dir: Path, config: dict[str, Any]) -> None:
    """
    Настраивает loguru для Django.
    """
    # ... implementation ...
```

### Description

This function is the main entry point for configuring Loguru. It removes default Loguru handlers, sets up new sinks, and configures the interception of standard `logging` messages.

### Arguments

*   `base_dir` (`Path`): The base directory of the project (e.g., `src/backend_django`).
*   `config` (`dict[str, Any]`): A dictionary containing logging-related settings, typically from Django's `settings` (e.g., `LOG_LEVEL_CONSOLE`, `LOG_LEVEL_FILE`, `LOG_ROTATION`, `DEBUG`).

### Process

1.  **Remove Default Loguru Handlers:** `logger.remove()` clears any pre-existing Loguru handlers to ensure a clean configuration.
2.  **Define Log Paths:**
    *   Creates a `logs/backend` subdirectory within `base_dir` to store log files.
    *   Defines paths for `debug.log` and `errors.json` within this directory.
3.  **Retrieve Configuration:** Extracts logging levels and rotation settings from the `config` dictionary.
4.  **Console Output:**
    *   Adds a sink for `sys.stdout` (console output).
    *   Configures `level` (e.g., `INFO`), `colorize=True`, and a custom format for readable console logs.
5.  **Debug File:**
    *   Adds a sink for `debug.log`.
    *   Configures `level` (e.g., `DEBUG`), `rotation` (e.g., "10 MB"), `compression="zip"`, and `enqueue=True` for asynchronous writing.
    *   Includes `backtrace=True` and `diagnose=True` for detailed error information.
6.  **Error JSON File:**
    *   Adds a sink for `errors.json`.
    *   Configures `level="ERROR"`, `serialize=True` (for JSON output), `rotation`, and `enqueue=True`.
7.  **Intercept Standard Logging:**
    *   `logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)`: Configures Python's standard `logging` to use `InterceptHandler`, effectively redirecting all standard log messages to Loguru.
8.  **Adjust Noisy Libraries:**
    *   Sets logging levels for specific Django components (`django`, `django.db.backends`, `django.utils.autoreload`) to reduce verbosity.
    *   If `DEBUG` is `False`, it sets `django.request` logging to `ERROR` to only log critical request errors.
9.  **Final Log:** Logs an informational message indicating that Loguru setup is complete.

## Usage

This `setup_logging` function is typically called once during the Django application's startup, as seen in `core/apps.py`.
