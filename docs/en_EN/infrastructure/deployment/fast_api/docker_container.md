# 🐳 Docker Container

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

The backend application is containerized using a multi-stage Dockerfile to ensure a small image size and security.

## Build Stages

### 1. Builder Stage
- **Base Image:** `python:3.12-slim`
- **Purpose:** Compile dependencies and prepare the virtual environment.
- **Actions:**
  - Installs system build dependencies (`gcc`, `libpq-dev`, etc.).
  - Creates a virtual environment at `/app/.venv`.
  - Installs Python requirements from `backend/requirements.txt`.

### 2. Runtime Stage
- **Base Image:** `python:3.12-slim`
- **Purpose:** Run the application in a minimal environment.
- **Actions:**
  - Installs runtime system libraries (`libpq5`, `libmagic1`, etc.).
  - Copies the virtual environment from the Builder stage.
  - Copies application code.
  - Sets up a non-root user `appuser` (UID 1000) for security.

## Configuration

- **Workdir:** `/app`
- **User:** `appuser`
- **Exposed Port:** `8000` (via uvicorn)
- **Healthcheck:** Curls `http://localhost:8000/health` every 30s.

## Start Command

The container starts with `uvicorn`:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
```

- `--proxy-headers`: Trusts headers from Nginx (X-Forwarded-For).
- `--forwarded-allow-ips='*'`: Trusts the upstream proxy (necessary in Docker dynamic networking).
