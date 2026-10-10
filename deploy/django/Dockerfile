# Multi-stage Dockerfile for DLC Montage Django Application
# Python 3.13 slim, non-root user, frozen lock deterministic dependencies

# ==========================================
# Stage 1: Build virtual environment
# ==========================================
FROM python:3.13-slim-bookworm AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# Install system dependencies needed to compile native wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv pinned to exact version
RUN pip install --no-cache-dir uv==0.11.8

WORKDIR /build

# Copy dependency files only for layer caching
COPY pyproject.toml uv.lock ./

# Synchronize dependencies deterministically against lockfile
RUN uv sync --frozen --no-dev --no-install-project

# ==========================================
# Stage 2: Runtime image
# ==========================================
FROM python:3.13-slim-bookworm AS runner

# Install only runtime shared libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged runtime user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src:/app/src/dlc_montage" \
    PORT=8000 \
    PRIVATE_MEDIA_ROOT="/app/data/private"

WORKDIR /app

# Copy prepared virtual environment from builder stage
COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv

# Create directories for staticfiles, media, and private files owned by unprivileged user
RUN mkdir -p /app/staticfiles /app/media /app/data/private && \
    chown -R appuser:appgroup /app

# Copy application sources
COPY --chown=appuser:appgroup src /app/src
COPY --chown=appuser:appgroup pyproject.toml /app/pyproject.toml

# Pre-collect static files during build as non-root user
USER appuser
RUN FIELD_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
    python src/dlc_montage/manage.py collectstatic --noinput --settings=dlc_montage.core.settings.dev

# Healthcheck probing health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; request = urllib.request.Request('http://127.0.0.1:8000/health/', headers={'X-Forwarded-Proto': 'https'}); urllib.request.urlopen(request).read()"

EXPOSE 8000

# Default web runtime command (Gunicorn)
CMD ["gunicorn", "dlc_montage.core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
