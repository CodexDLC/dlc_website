# 📜 Dockerfile

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This Dockerfile defines the multi-stage build process for the backend application. It optimizes for smaller image size and faster builds by separating the build environment from the runtime environment.

## Stage 1: Builder

*   **Base Image:** `python:3.13-slim`
*   **Working Directory:** `/app`
*   **Dependencies:** Installs `gcc`, `g++`, `libpq-dev` for building Python packages with C extensions.
*   **Poetry Setup:** Installs `poetry` and `poetry-plugin-export`.
*   **Dependency Export:**
    *   Copies `pyproject.toml` and `poetry.lock`.
    *   Runs `poetry lock` to ensure the lock file is up-to-date.
    *   Exports production dependencies (including `django` and `shared` group) to `requirements.txt`.
*   **Virtual Environment:** Creates a Python virtual environment at `/venv` and installs dependencies from `requirements.txt` into it.

## Stage 2: Runtime

*   **Base Image:** `python:3.13-slim`
*   **Working Directory:** `/app`
*   **Dependencies:** Installs `libpq5` (PostgreSQL client library) and `curl` (for health checks).
*   **User Setup:** Creates a non-root user `appuser` with UID 1000 for security.
*   **Copy Artifacts:**
    *   Copies the virtual environment from the `builder` stage to `/venv`.
    *   Copies the backend application code (`src/backend_django`) to `/app`.
    *   Copies the `entrypoint.sh` script to `/entrypoint.sh`.
*   **Permissions & Directories:**
    *   Creates necessary directories (`/app/staticfiles`, `/app/mediafiles`, `/app/logs/backend`).
    *   Changes ownership of `/app` to `appuser`.
    *   Makes `entrypoint.sh` executable.
*   **User:** Switches to `appuser`.
*   **Environment Variables:**
    *   `PATH`: Adds `/venv/bin` to the PATH to ensure Python executables from the virtual environment are used.
    *   `DJANGO_SETTINGS_MODULE`: Sets the default Django settings module to `core.settings.dev`.
*   **Healthcheck:** Defines a health check that uses `curl` to ping the backend's health endpoint.
*   **Working Directory:** Sets `/app` as the working directory.
*   **Entrypoint:** Sets `/entrypoint.sh` as the entrypoint for the container.
