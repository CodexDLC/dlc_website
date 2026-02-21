# 📂 Workers Architecture

[⬅️ Back](../../README.md) | [🏠 Docs Root](../../../README.md)

This directory contains the implementation of various background workers responsible for processing asynchronous tasks. Each worker is designed to handle specific types of jobs, ensuring that long-running or non-blocking operations do not impact the main application's responsiveness.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[📂 Core](./core/README.md)** | Core infrastructure and base classes for workers |
| **[📂 Notification Worker](./notification_worker/README.md)** | Worker dedicated to processing and sending notifications |
| **[📂 Templates](./templates/README.md)** | Templates for worker-related configurations or code generation |
