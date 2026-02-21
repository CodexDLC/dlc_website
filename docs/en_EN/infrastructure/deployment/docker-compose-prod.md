# 📜 Docker Compose (Production) (`docker-compose.prod.yml`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `docker-compose.prod.yml` file defines the multi-service Docker environment for deploying the Lily Website project in a production environment. It is optimized for production use, utilizing pre-built Docker images from a registry, `gunicorn` for the backend, and including services for SSL certificate management (Certbot) and Nginx.

## Purpose

The production `docker-compose.prod.yml` aims to:
*   Deploy a robust and scalable application stack.
*   Automate SSL certificate management with Certbot.
*   Serve the application securely via Nginx.
*   Ensure high availability with `restart: always` policies.
*   Integrate with GitHub Container Registry (GHCR) for image management.

## Services

### 1. `backend` (FastAPI/Django)

*   **Image:** `${DOCKER_IMAGE_BACKEND}` (pulled from GHCR, e.g., `ghcr.io/user/repo-backend:latest`)
*   **Container Name:** `lily_website-backend`
*   **Command:** Runs `gunicorn` to serve the Django/FastAPI application with 2 worker processes and a 90-second timeout.
*   **Env File:** `.env` (loaded from the `deploy/` directory on the VPS).
*   **Volumes:**
    *   `uploads`: Persistent volume for user-uploaded media files.
    *   `static_volume`: Persistent volume for collected static files.
    *   `logs_volume`: Persistent volume for application logs.
*   **Depends On:** `redis` (waits for it to be healthy).
*   **Healthcheck:** Checks a `/api/v1/health` endpoint on the backend.
*   **Restart Policy:** `always` (restarts if it stops).
*   **Network:** `lily_website-network`

### 2. `bot` (Telegram Bot)

*   **Image:** `${DOCKER_IMAGE_BOT}` (pulled from GHCR)
*   **Container Name:** `lily_website-telegram_bot`
*   **Env File:** `.env`
*   **Volumes:**
    *   `logs_volume`: Persistent volume for application logs.
*   **Restart Policy:** `always`.
*   **Depends On:** `redis` and `backend` (waits for them to be healthy).
*   **Network:** `lily_website-network`

### 3. `worker` (ARQ Notification Worker)

*   **Image:** `${DOCKER_IMAGE_WORKER}` (pulled from GHCR)
*   **Container Name:** `lily_website-worker_arq`
*   **Command:** Executes the ARQ worker with `src.workers.notification_worker.worker.WorkerSettings`.
*   **Env File:** `.env`
*   **Volumes:**
    *   `logs_volume`: Persistent volume for application logs.
*   **Restart Policy:** `always`.
*   **Depends On:** `redis` (waits for it to be healthy).
*   **Network:** `lily_website-network`

### 4. `redis`

*   **Image:** `redis:7-alpine`
*   **Container Name:** `lily_website-redis`
*   **Env File:** `.env`
*   **Command:** Starts Redis with a password (`REDIS_PASSWORD`) and AOF persistence enabled.
*   **Volumes:** `redis-data`: Persistent volume for Redis data.
*   **Healthcheck:** Checks if Redis is responsive and authenticates with `REDIS_PASSWORD`.
*   **Restart Policy:** `unless-stopped`.
*   **Network:** `lily_website-network`

### 5. `nginx`

*   **Image:** `${DOCKER_IMAGE_NGINX}` (pulled from GHCR)
*   **Container Name:** `lily_website-nginx`
*   **Ports:** Maps host ports `80` and `443` to container ports `80` and `443` respectively.
*   **Environment Variables:** Sets `DOMAIN_NAME` for Nginx configuration.
*   **Volumes:**
    *   `./nginx/nginx-main.conf:/etc/nginx/nginx.conf:ro`: Mounts the main Nginx configuration.
    *   `uploads`: Mounts user-uploaded media files (read-only).
    *   `static_volume`: Mounts collected static files (read-only).
    *   `certs_volume`: Mounts Let's Encrypt certificates (read-only).
    *   `certbot_challenge_volume`: Mounts volume for Certbot ACME challenges (read-only).
*   **Depends On:** `backend` (waits for it to be healthy).
*   **Restart Policy:** `always`.
*   **Logging:** Configures JSON file logging for Nginx.
*   **Network:** `lily_website-network`

### 6. `certbot`

*   **Image:** `certbot/certbot`
*   **Container Name:** `lily_website-certbot`
*   **Volumes:**
    *   `certs_volume`: Shared with Nginx for certificates.
    *   `certbot_challenge_volume`: Shared with Nginx for ACME challenges.
*   **Entrypoint:** Configures Certbot to continuously renew certificates every 12 hours.
*   **Network:** `lily_website-network`

## Volumes

*   `redis-data`: For Redis persistent data.
*   `uploads`: For user-uploaded media files (shared between backend and Nginx).
*   `static_volume`: For collected static files (shared between backend and Nginx).
*   `logs_volume`: For application logs (shared between backend, bot, and worker).
*   `certs_volume`: For Let's Encrypt SSL certificates (shared between Nginx and Certbot).
*   `certbot_challenge_volume`: For Certbot ACME challenge files (shared between Nginx and Certbot).

## Networks

*   `lily_website-network`: A custom bridge network to allow all services to communicate with each other.
