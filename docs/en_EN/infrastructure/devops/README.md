# 🚀 DevOps — CI/CD Pipeline

> `docs/en_EN/infrastructure/` · DevOps Overview

---

## Pipeline Overview

```
develop ──push──→ CI Develop (Lint: Ruff + Mypy)
    │
    └──PR──→ main ──→ CI Main (Tests + Docker Build Check)
                │
                └──tag (v*)──→ Deploy Production (Build → GHCR → Deploy)
```

**Note:** Production deployment now uses **git tags** instead of the `release` branch.

See: [Tag-Based Releases Guide](../deployment/releases_via_tags.md)

---

## Branches

| Branch | Purpose | Protection |
|:---|:---|:---|
| `develop` | Active development | CI lint on push |
| `main` | Stable code (production-ready) | PR only, CI tests required |

**Production Deployment:** Triggered by pushing tags matching `v*` pattern (e.g., `v1.2.3`)

---

## Workflows

| File | Trigger | Actions |
|:---|:---|:---|
| `ci-develop.yml` | Push to develop | Ruff lint + Mypy type check |
| `ci-main.yml` | PR to main | Full pytest + Docker build check |
| `deploy-production-tag.yml` | Push tag `v*` | Build images → GHCR → SSH deploy to VPS |

## Docker Architecture

See [docker.md](docker.md) for container architecture.

## Setup

See [github-secrets.md](github-secrets.md) for required secrets configuration.

---

## Module Map

| File | Description |
|:---|:---|
| [docker.md](docker.md) | Docker containers and compose architecture |
| [github-secrets.md](github-secrets.md) | GitHub repository secrets setup |
| [branching.md](branching.md) | Git branching strategy |
