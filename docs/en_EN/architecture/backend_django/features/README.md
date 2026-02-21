# 🧩 Features (Django Apps)

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../README.md)

This directory (`src/backend_django/features`) contains the modular Django applications, each representing a distinct feature or domain of the project. This structure promotes a "Feature-Sliced" architecture, where related code (models, views, URLs, templates) for a specific functionality is grouped together.

## Purpose

Organizing the backend into features (Django apps) helps to:
*   **Improve Modularity:** Each feature is a self-contained unit.
*   **Enhance Scalability:** Easier to manage and scale individual parts of the application.
*   **Increase Maintainability:** Changes in one feature are less likely to impact others.
*   **Facilitate Team Collaboration:** Different teams can work on different features concurrently.

## Module Map

| Component | Description |
|:---|:---|
| **[📂 Main Feature](./main/README.md)** | Core website pages, views, and static content. |
| **[📂 System Feature](./system/README.md)** | System-wide services, models (e.g., tags, mixins), and configurations. |
| **[📂 Booking Feature](./booking/README.md)** | Business logic for appointment booking and management. |
