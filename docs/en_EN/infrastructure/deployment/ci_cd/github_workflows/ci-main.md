# 📜 CI Main Workflow (`ci-main.yml`)

[⬅️ Back](README.md) | [🏠 Docs Root](../../../../../README.md)

This GitHub Actions workflow is triggered on every Pull Request targeting the `main` branch. Its primary purpose is to ensure the quality and stability of the code before it is merged into the `main` branch, which represents the stable codebase. It performs comprehensive linting, type checking, unit/integration tests, and verifies that Docker images can be built successfully.

## Trigger

*   **Event:** `pull_request`
*   **Target Branch:** `main`

## Jobs

### 1. `quality-and-tests`

This job performs static code analysis and runs the test suite.

*   **Runs on:** `ubuntu-latest`
*   **Steps:**
    1.  **Checkout Code:** Checks out the repository code.
    2.  **Set up Python:** Configures Python 3.13 environment.
    3.  **Install Poetry:** Installs the latest version of Poetry.
    4.  **Configure Poetry:** Configures Poetry to create virtual environments in-project.
    5.  **Load cached venv:** Attempts to restore a cached Poetry virtual environment to speed up dependency installation.
    6.  **Install dependencies:** Installs project dependencies using Poetry if the cache is not hit.
    7.  **Run Ruff:** Executes the `ruff` linter to check for code style violations and potential errors.
    8.  **Run Mypy:** Performs static type checking using `mypy`.
    9.  **Run Pytest:** Executes the `pytest` test suite.
        *   **Environment Variables:** `SECRET_KEY` and `ENVIRONMENT` are set for the test run.

### 2. `build-check`

This job verifies that all Docker images required for the project can be built successfully. This ensures that the application can be packaged and deployed without issues.

*   **Runs on:** `ubuntu-latest`
*   **Steps:**
    1.  **Checkout Code:** Checks out the repository code.
    2.  **Set up Docker Buildx:** Configures Docker Buildx for efficient Docker image building.
    3.  **Build Backend image:** Builds the Docker image for the backend service (`deploy/backend/Dockerfile`).
        *   `push: false`: The image is built but not pushed to a registry.
        *   `cache-from`, `cache-to`: Uses GitHub Actions cache for Docker layers to speed up builds.
    4.  **Build Bot image:** Builds the Docker image for the Telegram bot service (`deploy/bot/Dockerfile`).
    5.  **Build Worker image:** Builds the Docker image for the worker service (`deploy/worker/Dockerfile`).
    6.  **Build Nginx image:** Builds the Docker image for the Nginx service (`deploy/nginx/Dockerfile`).
