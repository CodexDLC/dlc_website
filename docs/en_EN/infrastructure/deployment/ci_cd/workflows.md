# 🚀 Workflows

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

The project uses GitHub Actions to automate testing, linting, and deployment.

## Pipelines

### 1. CI Main (`ci-main.yml`)
- **Trigger:** Pull Request to `main`.
- **Jobs:**
  - **Tests:** Runs `pytest` with a service container (`postgres:15`).
  - **Build Check:** Verifies that the Docker image builds successfully.

### 2. CI Develop (`ci-develop.yml`)
- **Trigger:** Push to `develop`.
- **Jobs:**
  - **Lint:** Runs `ruff` (style) and `mypy` (types) to ensure code quality during development.

### 3. CD Release (`cd-release.yml`)
- **Trigger:** Push to `release`.
- **Jobs:**
  - **Deploy:**
    1. Builds Backend and Nginx Docker images.
    2. Pushes images to GitHub Container Registry (GHCR).
    3. Copies `docker-compose.prod.yml` to the VPS via SCP.
    4. Connects via SSH to:
       - Update `.env` file.
       - Pull new images.
       - Restart containers (`docker compose up -d`).
       - Run database migrations (`alembic upgrade head`).
       - Prune old images.

### 4. Protect Release (`check-release-source.yml`)
- **Trigger:** Pull Request to `release`.
- **Logic:** Fails if the source branch is not `main`.
- **Goal:** Enforces the Git Flow: `develop` -> `main` -> `release`.
