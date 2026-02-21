# 📜 Dockerfile

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This Dockerfile defines the multi-stage build process for the Telegram bot application. It optimizes for smaller image size and faster builds by separating the build environment from the runtime environment.

## Stage 1: Builder

*   **Base Image:** `python:3.13-slim`
*   **Working Directory:** `/app`
*   **Poetry Setup:** Installs `poetry` and `poetry-plugin-export`.
*   **Dependency Export:**
    *   Copies `pyproject.toml` and `poetry.lock`.
    *   Runs `poetry lock` to ensure the lock file is up-to-date.
    *   Exports production dependencies (including `bot` and `shared` groups) to `requirements.txt`.
*   **Virtual Environment:** Creates a Python virtual environment at `/app/.venv` and installs dependencies from `requirements.txt` into it.

## Stage 2: Runtime

*   **Base Image:** `python:3.13-slim`
*   **Working Directory:** `/app`
*   **User Setup:** Creates a non-root user `appuser` with UID 1000 for security.
*   **Copy Artifacts:**
    *   Copies the virtual environment from the `builder` stage to `/app/.venv`.
    *   Copies the Telegram bot application code (`src/telegram_bot`) to `/app/src/telegram_bot`.
    *   Copies the shared code (`src/shared`) to `/app/src/shared`.
*   **Permissions:** Changes ownership of `/app` to `appuser`.
*   **User:** Switches to `appuser`.
*   **Environment Variables:**
    *   `PATH`: Adds `/app/.venv/bin` to the PATH to ensure Python executables from the virtual environment are used.
    *   `PYTHONPATH`: Adds `/app` to the `PYTHONPATH` to allow Python to find modules within the application directory.
*   **Command:** Sets the default command to run the Telegram bot application using `python -m src.telegram_bot.app_telegram`.
