# 📜 Config

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This module defines the `WorkerSettings` class, which extends `CommonSettings` and is responsible for managing all environment-specific configurations for the ARQ worker application. It uses Pydantic for robust settings validation and provides convenient properties for accessing parsed values.

## `WorkerSettings` Class

The `WorkerSettings` class encapsulates various configuration parameters, including SMTP settings for email, template directory paths, ARQ-specific settings, and Redis connection details.

### Fields

*   `SMTP_HOST` (`str`): The SMTP server host (default: `"smtp.spacemail.com"`).
*   `SMTP_PORT` (`int`): The SMTP server port (default: `465`).
*   `SMTP_USER` (`str`): The username for SMTP authentication.
*   `SMTP_PASSWORD` (`str`): The password for SMTP authentication.
*   `SMTP_FROM_EMAIL` (`str`): The email address from which notifications will be sent.
*   `SMTP_USE_TLS` (`bool`): Whether to use TLS for SMTP connection (default: `True`).
*   `TEMPLATES_DIR` (`str`): The directory where email templates are located (default: `"src/workers/templates"`).
*   `arq_max_jobs` (`int`): The maximum number of jobs an ARQ worker can process concurrently (default: `10`).
*   `arq_job_timeout` (`int`): The maximum time (in seconds) a job is allowed to run before being considered failed (default: `60`).
*   `arq_keep_result` (`int`): The time (in seconds) to keep job results in Redis (default: `60`).
*   `redis_url_env` (`str | None`): The Redis connection URL, can be set via `REDIS_URL` environment variable.

### Properties

*   `arq_redis_settings` (`RedisSettings`):
    A property that returns an instance of `arq.connections.RedisSettings` configured with the worker's Redis host, port, and password. This is used by the ARQ library to establish Redis connections.
