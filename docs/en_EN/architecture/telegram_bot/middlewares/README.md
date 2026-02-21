# 📂 Middlewares

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../README.md)

This directory contains Aiogram middlewares, which are functions or classes that process incoming updates before they reach the handlers. Middlewares are used for cross-cutting concerns such as authentication, throttling, logging, and dependency injection.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[📜 Security](./security.md)** | Middleware for security-related checks and access control |
| **[📜 Container](./container.md)** | Middleware for injecting the DI container into handlers |
| **[📜 Throttling](./throttling.md)** | Middleware for preventing flood attacks and rate limiting |
| **[📜 User Validation](./user_validation.md)** | Middleware for validating and preparing user data |
