# 📂 Director Service

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../../README.md)

This directory contains the `Director` service, which is responsible for managing global navigation and scene transitions within the Telegram bot. It orchestrates the flow between different features (scenes) and ensures that the correct orchestrator is active for the current user state.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[📜 Director](./director.md)** | Core service for global navigation and scene management |
| **[📜 Registry](./registry.md)** | Registry for mapping feature keys to orchestrator instances |
