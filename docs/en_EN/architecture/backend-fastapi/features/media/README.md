# 🖼️ Media Feature

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../../README.md)

The Media feature is responsible for uploading, storing, processing, and serving images. It is a core functionality of PinLite.

## 🏗️ Layer Structure

The feature is organized according to Clean Architecture principles.

### 1. [🗄️ Database Schema](./database_schema.md)
Description of database tables:
*   `files` — Physical storage (CAS).
*   `images` — User metadata.

### 2. [📜 Contracts (Repositories)](./contracts.md)
Interface `IMediaRepository` for data abstraction (deduplication, search, deletion).

### 3. [🧠 Business Logic (Services)](./services.md)
`MediaService` handles:
*   Upload and deduplication algorithm.
*   Thumbnail generation.
*   Garbage Collection.

### 4. [🔌 API Layer](./api.md)
Description of HTTP endpoints:
*   Upload (`/upload`)
*   Feed (`/feed`)
*   View and delete.

### 5. [🧪 Testing Strategy](./tests_spec.md)
Unit and integration testing specifications. Tests are located inside the feature folder: `src/backend-fastapi/features/media/tests`.

## 📚 Specifications

*   **[💾 Storage & Validation (CAS)](./storage_spec.md)** — Detailed specification of the file storage and validation algorithm.
