# 📂 GitHub Workflows

[⬅️ Back](../../../README.md) | [🏠 Docs Root](../../../../../README.md)

This directory contains documentation for the GitHub Actions workflows used in the project. These workflows automate various aspects of the development lifecycle, including continuous integration (CI), continuous deployment (CD), and code quality checks.

---

## 🗺️ Active Workflows

| Component | Description |
|:---|:---|
| **[📜 CI Develop Workflow](ci-develop.md)** | Workflow for CI checks (lint, type checking) on `develop` branch pushes |
| **[📜 CI Main Workflow](ci-main.md)** | Workflow for CI checks (full tests, Docker build) on `main` branch Pull Requests |

---

## 📦 Deployment

**Production deployment** now uses **tag-based releases** instead of the `release` branch.

**Workflow:** `.github/workflows/deploy-production-tag.yml`

**Trigger:** Push git tags matching `v*` pattern (e.g., `v1.2.3`)

**Documentation:** [Tag-Based Releases Guide](../../releases_via_tags.md)

---

## 🗄️ Archived Workflows (No Longer Active)

The following workflows were part of the old `release` branch workflow and have been removed:

| Component | Status | Replacement |
|:---|:---|:---|
| ~~CD Release Workflow (`cd-release.yml`)~~ | **Removed** | `deploy-production-tag.yml` (tag-based) |
| ~~Check Release Source (`check-release-source.yml`)~~ | **Removed** | No longer needed (no release branch) |

**Migration Guide:** [MIGRATION_TO_TAGS.md](../../MIGRATION_TO_TAGS.md)
