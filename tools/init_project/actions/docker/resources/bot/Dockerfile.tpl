# === STAGE 1: Builder ===
FROM python:{{PYTHON_VERSION}}-slim AS builder

WORKDIR /app

RUN python -m venv /app/.venv

# Install dependencies via pyproject.toml
COPY pyproject.toml ./
RUN /app/.venv/bin/pip install --no-cache-dir ".[bot]"

# === STAGE 2: Runtime ===
FROM python:{{PYTHON_VERSION}}-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/telegram_bot /app/src/telegram_bot
COPY src/shared /app/src/shared

RUN chown -R appuser:appuser /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

# Start bot
CMD ["python", "-m", "src.telegram_bot.app_telegram"]
