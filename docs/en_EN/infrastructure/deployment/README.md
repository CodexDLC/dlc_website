# 📂 Deployment Documentation

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../README.md)

This folder contains documentation regarding project deployment, infrastructure, and automation.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[🏷️ Releases via Tags](./releases_via_tags.md)** | **Primary Guide:** Tag-based production release workflow |
| **[📜 Docker Compose (Development)](./docker-compose-dev.md)** | Docker Compose configuration for local development environments. |
| **[📜 Docker Compose (Production)](./docker-compose-prod.md)** | Docker Compose configuration for production deployment. |
| **[📂 Nginx](./nginx/README.md)** | Web server and reverse proxy configuration |
| **[📂 CI/CD](./ci_cd/README.md)** | GitHub Actions pipelines |

---

## 📋 Quick Start: How to Release

```bash
# 1. Merge develop → main via PR on GitHub
# 2. Create tag:
git checkout main
git pull origin main
git tag -a v1.2.3 -m "Release 1.2.3: Production fixes"
git push origin v1.2.3

# 3. GitHub Actions automatically deploys!
```

Full guide: [Releases via Tags](./releases_via_tags.md)
