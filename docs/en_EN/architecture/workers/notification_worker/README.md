# 📂 Notification Worker

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../README.md)

This directory contains the implementation of the Notification Worker, a dedicated ARQ worker responsible for processing and sending various types of notifications (e.g., emails). It defines the worker's configuration, tasks, services, and dependencies.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[📜 Config](./config.md)** | Configuration settings specific to the Notification Worker |
| **[📜 Worker](./worker.md)** | Main ARQ worker definition and task registration |
| **[📜 Dependencies](./dependencies.md)** | Dependency injection setup for the Notification Worker |
| **[📂 Tasks](./tasks/README.md)** | Definitions of individual asynchronous tasks processed by the worker |
| **[📂 Services](./services/README.md)** | Services used by the Notification Worker tasks |
