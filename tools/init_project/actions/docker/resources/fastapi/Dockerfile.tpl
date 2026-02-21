# === STAGE 1: Builder ===
FROM python:{{PYTHON_VERSION}}-slim AS builder

WORKDIR /app

# System dependencies for build
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /app/.venv

# Install dependencies via pyproject.toml
COPY pyproject.toml ./
RUN /app/.venv/bin/pip install --no-cache-dir ".[fastapi]"

# === STAGE 2: Runtime ===
FROM python:{{PYTHON_VERSION}}-slim

WORKDIR /app

# System dependencies for runtime
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/backend_fastapi /app/src/backend_fastapi
COPY src/shared /app/src/shared

# Create data directories
RUN mkdir -p /app/data/uploads /app/data/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "src.backend_fastapi.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
