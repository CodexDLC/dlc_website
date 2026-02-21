# ⚙️ Core Backend Configuration

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../README.md)

This directory (`src/backend_django/core`) contains the core configuration and infrastructure files for the Django backend project. It centralizes settings, URL routing, WSGI/ASGI configurations, and other project-wide utilities.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[📂 Settings](./settings/README.md)** | Django settings files for different environments (base, dev, prod). |
| **[📜 URLs](./urls.md)** | Root URL configuration for the entire Django project. |
| **[📜 WSGI](./wsgi.md)** | WSGI configuration for deploying Django applications. |
| **[📜 ASGI](./asgi.md)** | ASGI configuration for deploying asynchronous Django applications. |
| **[📜 Apps](./apps.md)** | Application configuration for the `core` app. |
| **[📜 Views](./views.md)** | Project-wide views (e.g., custom error pages). |
| **[📜 Logger](./logger.md)** | Centralized logging configuration. |
| **[📜 Cache](./cache.md)** | Cache configuration and utilities. |
| **[📜 Sitemaps](./sitemaps.md)** | Sitemaps generation configuration. |
| **[📂 ARQ](./arq/README.md)** | ARQ-related configurations and tasks for background processing. |
