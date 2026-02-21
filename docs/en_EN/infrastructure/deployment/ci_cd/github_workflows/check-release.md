# 📜 Check Release Source Workflow (`check-release-source.yml`)

[⬅️ Back](README.md) | [🏠 Docs Root](../../../../../README.md)

---

> **⚠️ ARCHIVED WORKFLOW**
>
> This workflow has been **removed** as part of migration to tag-based deployment.
>
> **Reason:** No longer needed - `release` branch was removed.
>
> **Current approach:** [Tag-Based Releases Guide](../../releases_via_tags.md)
>
> **Migration guide:** [MIGRATION_TO_TAGS.md](../../MIGRATION_TO_TAGS.md)

---

## Historical Documentation (For Reference)

This GitHub Actions workflow was designed to enforce the project's Git Flow strategy, specifically for the `release` branch. It ensured that Pull Requests targeting the `release` branch originated only from the `main` branch, preventing unauthorized or out-of-flow merges.

## Trigger

*   **Event:** `pull_request`
*   **Target Branch:** `release`

## Jobs

### 1. `check-source-branch`

This job verifies the source branch of any Pull Request targeting `release`.

*   **Runs on:** `ubuntu-latest`
*   **Steps:**
    1.  **Check source branch:** This step contains a conditional check (`if: github.head_ref != 'main'`).
        *   **Logic:** If the source branch (`github.head_ref`) of the Pull Request is *not* `main`, the workflow fails.
        *   **Output:** It prints an error message to the console, explicitly stating that merges into `release` are allowed only from `main`, and then exits with a non-zero status code, causing the workflow to fail.

## Purpose

This workflow is a critical part of the Continuous Deployment (CD) pipeline's protection mechanisms. By enforcing that `release` can only be updated from `main`, it ensures:
*   **Controlled Deployment:** Only thoroughly tested and stable code (from `main`) can be deployed to production.
*   **Git Flow Adherence:** Reinforces the `develop` -> `main` -> `release` branching model.
*   **Reduced Errors:** Minimizes the risk of deploying untested features or hotfixes directly to production.
