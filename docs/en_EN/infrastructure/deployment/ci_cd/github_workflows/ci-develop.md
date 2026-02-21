# 📜 CI Develop Workflow (`ci-develop.yml`)

[⬅️ Back](README.md) | [🏠 Docs Root](../../../../../README.md)

This GitHub Actions workflow is designed for a fast quality check during active development. It is triggered on every push or Pull Request targeting the `develop` branch. The workflow focuses on linting and type checking to ensure code quality early in the development cycle.

## Trigger

*   **Event:** `push` to `develop` branch.
*   **Event:** `pull_request` to `develop` branch.

## Jobs

### 1. `lint`

This job performs static code analysis (linting) and type checking.

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
