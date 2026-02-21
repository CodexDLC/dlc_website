# 📂 Django Settings

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../../README.md)

This directory (`src/backend_django/core/settings`) contains the Django settings files, organized by environment. This modular approach allows for easy management of configurations specific to development, production, and testing environments, while sharing common settings.

## Purpose

The settings files define all the configurable aspects of the Django project, including database connections, installed applications, middleware, static file handling, security keys, and more. Separating them by environment ensures that each deployment context has its appropriate configuration.

## Module Map

| Component | Description |
|:---|:---|
| **[📜 Base Settings](./base.md)** | Common settings applied across all environments. |
| **[📜 Development Settings](./dev.md)** | Settings specific to the local development environment. |
| **[📜 Production Settings](./prod.md)** | Settings specific to the production deployment environment. |
| **[📜 Test Settings](./test.md)** | Settings specific to the testing environment. |
