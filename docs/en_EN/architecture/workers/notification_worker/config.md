# 📜 Notification Worker — Configuration

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

The Notification Worker uses a single configuration class: `WorkerSettings` from `src/workers/core/config.py`.
There is **no separate config** in `notification_worker/` — this was intentionally removed to avoid duplication.

## `WorkerSettings` (from `src/workers/core/config.py`)

Inherits from `CommonSettings` (shared Redis, logging config).

### Fields

| Field             | Type    | Default              | Description                        |
|-------------------|---------|----------------------|------------------------------------|
| `SMTP_HOST`       | `str`   | `"smtp.spacemail.com"` | SMTP server hostname             |
| `SMTP_PORT`       | `int`   | `465`                | SMTP port (465=SSL, 587=STARTTLS)  |
| `SMTP_USER`       | `str`   | required             | SMTP login (from `.env`)           |
| `SMTP_PASSWORD`   | `str`   | required             | SMTP password (from `.env`)        |
| `SMTP_FROM_EMAIL` | `str`   | required             | From address for outgoing mail     |
| `SMTP_USE_TLS`    | `bool`  | `True`               | Enable TLS                         |
| `TEMPLATES_DIR`   | `str`   | `"src/workers/templates"` | Path to Jinja2 templates      |
| `arq_max_jobs`    | `int`   | `10`                 | Max parallel ARQ jobs              |
| `arq_job_timeout` | `int`   | `60`                 | Job timeout in seconds             |
| `arq_keep_result` | `int`   | `60`                 | How long to keep job results (sec) |

All fields can be overridden via `.env` file or environment variables.

### Inherited from `CommonSettings`

| Field              | Default       | Description                    |
|--------------------|---------------|--------------------------------|
| `redis_host`       | `"localhost"` | Redis host                     |
| `redis_port`       | `6379`        | Redis port                     |
| `redis_password`   | `None`        | Redis password                 |
| `debug`            | `True`        | Dev/prod mode                  |
| `log_level_console`| `"DEBUG"`     | Console log level              |

## Usage in worker.py

```python
from src.workers.core.config import WorkerSettings as CoreWorkerSettings

settings = CoreWorkerSettings()  # Loaded from .env at startup

class WorkerSettings(BaseArqSettings):
    redis_settings = RedisSettings(
        host=settings.effective_redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
    )
    max_jobs = settings.arq_max_jobs
    ...
```
