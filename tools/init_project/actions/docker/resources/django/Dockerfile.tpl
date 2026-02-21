# === STAGE 1: Builder ===
FROM python:{{PYTHON_VERSION}}-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry poetry-plugin-export

COPY pyproject.toml poetry.lock ./
# Экспортируем основные зависимости + django + shared
RUN poetry export --without-hashes --with django,shared --format=requirements.txt > requirements.txt

RUN python -m venv /venv
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# === STAGE 2: Runtime ===
FROM python:{{PYTHON_VERSION}}-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser

COPY --from=builder /venv /venv
COPY src/backend_django /app

RUN mkdir -p /app/staticfiles /app/mediafiles /app/logs/backend && \
    chown -R appuser:appuser /app

USER appuser

ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV DJANGO_SETTINGS_MODULE="core.settings.prod"

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Entrypoint script will handle migrations and static
COPY deploy/django/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
