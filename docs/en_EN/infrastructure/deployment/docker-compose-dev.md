# 📜 Docker Compose (Development) (`docker-compose.yml`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `docker-compose.yml` file defines the multi-service Docker environment for local development of the Lily Website project. It sets up all necessary services, including databases, application containers, and development tools, allowing developers to run the entire application stack with a single command.

## Purpose

The development `docker-compose.yml` aims to:
*   Provide a consistent and isolated development environment.
*   Simplify the setup and management of project dependencies (PostgreSQL, Redis).
*   Enable hot-reloading for application code (via bind mounts).
*   Include development-specific tools like Mailpit for email testing.

## Services

### 1. `db` (PostgreSQL)

*   **Image:** `postgres:16-alpine`
*   **Container Name:** `lily_website-db`
*   **Volumes:**
    *   `postgres_data`: Persistent volume for database data.
    *   `../scripts/init_db_schemas.sql`: Mounts a script to initialize database schemas on container startup.
*   **Environment Variables:** Sets `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
*   **Healthcheck:** Checks if PostgreSQL is ready to accept connections.
*   **Network:** `lily_website-network`

### 2. `redis`

*   **Image:** `redis:7-alpine`
*   **Container Name:** `lily_website-redis`
*   **Env File:** `../.env` (loads environment variables from the project's root `.env` file).
*   **Command:** Starts Redis with a password (`REDIS_PASSWORD`) and AOF persistence enabled.
*   **Ports:** Maps host port `6380` to container port `6379`.
*   **Volumes:** `redis-data`: Persistent volume for Redis data.
*   **Healthcheck:** Checks if Redis is responsive and authenticates with `REDIS_PASSWORD`.
*   **Network:** `lily_website-network`

### 3. `backend` (FastAPI/Django)

*   **Build:** Uses `deploy/backend/Dockerfile` to build the image from the project root.
*   **Container Name:** `lily_website-backend`
*   **Ports:** Maps host port `8000` to container port `8000`.
*   **Env File:** `../.env`
*   **Volumes:**
    *   `../src/backend_django:/app`: Mounts the backend source code for hot-reloading.
    *   `uploads`: Volume for user-uploaded media files.
    *   `static_volume`: Volume for collected static files.
    *   `logs_volume`: Volume for application logs.
*   **Depends On:** `db` and `redis` (waits for them to be healthy).
*   **Healthcheck:** Checks a `/api/v1/health` endpoint on the backend.
*   **Network:** `lily_website-network`

### 4. `bot` (Telegram Bot)

*   **Build:** Uses `deploy/bot/Dockerfile` to build the image.
*   **Container Name:** `lily_website-telegram_bot`
*   **Env File:** `../.env`
*   **Volumes:**
    *   `../src/telegram_bot:/app/src/telegram_bot:ro`: Mounts the bot's source code (read-only).
    *   `../src/shared:/app/src/shared:ro`: Mounts shared code (read-only).
*   **Depends On:** `redis` and `backend` (waits for them to be healthy).
*   **Network:** `lily_website-network`

### 5. `worker` (ARQ Notification Worker)

*   **Build:** Uses `deploy/worker/Dockerfile` to build the image.
*   **Container Name:** `lily_website-notification_worker`
*   **Command:** Executes the ARQ worker with `src.workers.notification_worker.worker.WorkerSettings`.
*   **Env File:** `../.env`
*   **Volumes:**
    *   `../src/workers:/app/src/workers:ro`: Mounts the worker's source code (read-only).
    *   `../src/shared:/app/src/shared:ro`: Mounts shared code (read-only).
    *   `logs_volume`: Volume for application logs.
*   **Depends On:** `redis` and `backend` (waits for them to be healthy).
*   **Network:** `lily_website-network`

### 6. `nginx`

*   **Build:** Uses `deploy/nginx/Dockerfile` to build the image.
*   **Container Name:** `lily_website-nginx`
*   **Ports:** Maps host port `8080` to container port `80`.
*   **Volumes:**
    *   `uploads`: Mounts user-uploaded media files (read-only).
    *   `static_volume`: Mounts collected static files (read-only).
*   **Depends On:** `backend` (waits for it to be healthy).
*   **Network:** `lily_website-network`

### 7. `mailpit`

*   **Image:** `axllent/mailpit:latest`
*   **Container Name:** `lily_website-mailpit`
*   **Ports:**
    *   `8025:8025`: Web UI for Mailpit.
    *   `1025:1025`: SMTP server for Mailpit.
*   **Environment Variables:** Configures Mailpit behavior (max messages, SMTP authentication).
*   **Network:** `lily_website-network`

## Volumes

*   `postgres_data`: For PostgreSQL persistent data.
*   `redis-data`: For Redis persistent data.
*   `uploads`: For user-uploaded media files (shared between backend and Nginx).
*   `static_volume`: For collected static files (shared between backend and Nginx).
*   `logs_volume`: For application logs (shared between backend and worker).

## Networks

*   `lily_website-network`: A custom bridge network to allow all services to communicate with each other.
