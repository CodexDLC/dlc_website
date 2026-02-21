# 📂 Nginx Deployment

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../README.md)

This directory contains the Docker-related files and configuration for deploying the Nginx reverse proxy and web server. It includes Dockerfiles for production and local development, along with various Nginx configuration files.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[📜 Dockerfile](./Dockerfile.md)** | Defines how the production Nginx Docker image is built. |
| **[📜 Dockerfile.local](./Dockerfile.local.md)** | Defines how the local development Nginx Docker image is built. |
| **[📜 Nginx Main Configuration](./nginx-main.md)** | Main Nginx configuration file (`nginx-main.conf`). |
| **[📜 Site Configuration](./site.md)** | Production Nginx site configuration (`site.conf`). |
| **[📜 Local Site Configuration](./site-local.md)** | Local development Nginx site configuration (`site-local.conf`). |
| **[📜 Site Configuration Template](./site-template.md)** | Template for generating Nginx site configurations (`site.conf.template`). |
