# === STAGE 1: Builder ===
FROM python:{{PYTHON_VERSION}}-slim AS builder
WORKDIR /app

RUN pip install poetry poetry-plugin-export

COPY pyproject.toml poetry.lock ./
RUN poetry export --with workers,shared --without-hashes --format=requirements.txt > requirements.txt

RUN python -m venv /app/.venv
RUN /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# === STAGE 2: Runtime ===
FROM python:{{PYTHON_VERSION}}-slim
WORKDIR /app

RUN useradd -m -u 1000 appuser

COPY --from=builder /app/.venv /app/.venv

COPY src/workers /app/src/workers
COPY src/shared /app/src/shared

# Create logs directory and set permissions
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"
