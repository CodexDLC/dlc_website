# 📜 CD Release Workflow (`cd-release.yml`)

[⬅️ Back](README.md) | [🏠 Docs Root](../../../../../README.md)

---

> **⚠️ ARCHIVED WORKFLOW**
>
> This workflow has been **removed** and replaced with tag-based deployment.
>
> **Current workflow:** `.github/workflows/deploy-production-tag.yml`
>
> **Documentation:** [Tag-Based Releases Guide](../../releases_via_tags.md)
>
> **Migration guide:** [MIGRATION_TO_TAGS.md](../../MIGRATION_TO_TAGS.md)

---

## Historical Documentation (For Reference)

This GitHub Actions workflow was responsible for Continuous Deployment (CD) to the production server. It was triggered when code was pushed to the `release` branch or could be manually dispatched. The workflow built Docker images, pushed them to GitHub Container Registry (GHCR), and then deployed the updated application to a remote VPS via SSH.

## Trigger

*   **Event:** `push` to `release` branch.
*   **Manual Trigger:** `workflow_dispatch` (allows manual execution from GitHub Actions UI).

## Jobs

### 1. `pre-deploy-check`

This job performs a preliminary check to ensure that the deployment target (VPS) is accessible via SSH.

*   **Runs on:** `ubuntu-latest`
*   **Steps:**
    1.  **Test SSH Connection:** Uses `appleboy/ssh-action` to attempt an SSH connection to the VPS. This acts as a quick health check before proceeding with the main deployment.
        *   **Secrets Used:** `secrets.HOST`, `secrets.USERNAME`, `secrets.SSH_KEY`.

### 2. `deploy`

This is the main deployment job. It depends on `pre-deploy-check` to ensure the server is reachable.

*   **Needs:** `pre-deploy-check`
*   **Runs on:** `ubuntu-latest`
*   **Permissions:** `contents: read`, `packages: write` (required for pushing to GHCR).
*   **Steps:**
    1.  **Checkout Code:** Checks out the repository code.
    2.  **Lowercase repo name:** Converts the GitHub repository name to lowercase and stores it in an environment variable `REPO_LOWER` for use in Docker image tags.
    3.  **Set up Docker Buildx:** Configures Docker Buildx for efficient Docker image building.
    4.  **Log in to GHCR:** Authenticates with GitHub Container Registry using `github.actor` (the user who triggered the workflow) and `secrets.GITHUB_TOKEN`.
    5.  **Build and Push Backend:** Builds the Docker image for the backend service (`deploy/backend/Dockerfile`) and pushes it to GHCR with `latest` and `github.sha` tags.
        *   **Cache:** Uses GHCR as a build cache to speed up subsequent builds.
    6.  **Build and Push Bot:** Builds and pushes the Docker image for the Telegram bot service (`deploy/bot/Dockerfile`).
    7.  **Build and Push Worker:** Builds and pushes the Docker image for the worker service (`deploy/worker/Dockerfile`).
    8.  **Build and Push Nginx:** Builds and pushes the Docker image for the Nginx service (`deploy/nginx/Dockerfile`).
    9.  **Copy configs to VPS:** Uses `appleboy/scp-action` to securely copy the `deploy/` directory (containing `docker-compose.prod.yml` and Nginx configs) to the `/opt/lily_website/` directory on the VPS.
        *   **Secrets Used:** `secrets.HOST`, `secrets.USERNAME`, `secrets.SSH_KEY`.
    10. **SSH Deploy:** Connects to the VPS via SSH and executes a series of commands to update and restart the application.
        *   **Environment Variables Passed to SSH:** `DOCKER_IMAGE_BACKEND`, `DOCKER_IMAGE_BOT`, `DOCKER_IMAGE_WORKER`, `DOCKER_IMAGE_NGINX` (all tagged with `:latest`), `DOMAIN_NAME`, `REDIS_PASSWORD`, `GITHUB_TOKEN`, `GITHUB_ACTOR`.
        *   **Script Executed on VPS:**
            *   Navigates to `/opt/lily_website/deploy`.
            *   Creates a `.env` file from `secrets.ENV_FILE` content.
            *   Updates specific environment variables (`DOCKER_IMAGE_*`, `DOMAIN_NAME`, `REDIS_PASSWORD`) within the `.env` file.
            *   Logs in to GHCR using the provided `GITHUB_TOKEN` and `GITHUB_ACTOR`.
            *   Pulls the latest Docker images defined in `docker-compose.prod.yml`.
            *   **Runs Database Migrations:** Executes `python manage.py migrate --noinput` within the `backend` container. If migrations fail, the deployment is aborted.
            *   **Collects Static Files:** Executes `python manage.py collectstatic --noinput` within the `backend` container.
            *   Starts/restarts Docker containers using `docker compose up -d --remove-orphans --wait --wait-timeout 120`, waiting for services to become healthy.
            *   Checks the health of running containers using `docker compose ps`.
            *   Prunes old Docker images to free up disk space.
            *   Logs a success message.
