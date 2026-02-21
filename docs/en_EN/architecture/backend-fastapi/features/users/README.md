# 👤 Users Feature

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../../README.md)

The Users feature is responsible for identification, authentication, and profile management.

## 🏗️ Layer Structure

The feature is organized according to Clean Architecture principles. Each layer has its own responsibility and specification.

### 1. [🗄️ Database Schema](./database_schema.md)
Description of database tables (`users`, `refresh_tokens`). This is the data infrastructure layer.

### 2. [📜 Contracts (Repositories)](./contracts.md)
Interfaces (Protocols) for data access. Business logic depends on these contracts, not on the direct SQLAlchemy implementation.

### 3. [🧠 Business Logic (Services)](./services.md)
Pure business logic: registration, password validation, token generation. Services orchestrate repositories and security utilities.

### 4. [🔌 API Layer](./api.md)
Description of HTTP endpoints (Routers). The presentation layer that accepts requests and calls services.

### 5. [🧪 Testing Strategy](./tests_spec.md)
Unit and integration testing specifications. Tests are located inside the feature folder: `src/backend-fastapi/features/users/tests`.
