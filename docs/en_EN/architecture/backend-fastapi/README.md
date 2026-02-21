# 📂 Backend FastAPI Architecture

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../README.md)

Documentation and development plans for the server-side application located in `src/backend-fastapi`.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[📂 Core Infrastructure](./core/README.md)** | Base configuration, logging, security, and exceptions |
| **[📂 Database Layer](./database/README.md)** | SQLAlchemy models, migrations, and repositories |
| **[📂 Features (Domains)](./features/README.md)** | Business logic modules (Users, Media, etc.) |
| **[📂 Flows (Processes)](./flows/README.md)** | Authentication and data flow specifications |
| **[📂 Dependencies](./dependencies/README.md)** | External services and libraries |
| **[📂 Tasks](./tasks/README.md)** | Project tasks and audit logs |
| **[🗺️ Roadmap](./roadmap.md)** | Global development plan and branches |
| **[🌿 Git Flow](./git_flow.md)** | Branching strategy and release process |

## 🏗️ Project Structure

Below is the structure of the `src/backend-fastapi` directory.

### Application Code

```text
src/backend-fastapi/
 ┣ 📂 core                  # Infrastructure Layer (Config, DB Connect, Logs)
 ┃ ┣ 📂 schemas             # Base Pydantic Schemas (BaseRequest, BaseResponse)
 ┃ ┃ ┣ 📜 base.py
 ┃ ┃ ┗ 📜 error.py
 ┃ ┣ 📜 config.py
 ┃ ┣ 📜 database.py
 ┃ ┣ 📜 dependencies.py     # FastAPI Dependencies (get_current_user)
 ┃ ┣ 📜 exceptions.py       # Error Handling
 ┃ ┣ 📜 logger.py
 ┃ ┗ 📜 security.py
 ┃
 ┣ 📂 database              # Data Layer (Infrastructure)
 ┃ ┣ 📂 models              # SQLAlchemy Models (DB Tables)
 ┃ ┗ 📂 repositories        # Repository Implementations
 ┃
 ┣ 📂 features              # Domain Layer (Business Features)
 ┃ ┣ 📂 users               # Domain: Users
 ┃ ┃ ┣ 📂 api               # Controllers (Routers)
 ┃ ┃ ┣ 📂 contracts         # Interfaces (Repository Protocols)
 ┃ ┃ ┣ 📂 services          # Business Logic
 ┃ ┃ ┗ 📂 schemas           # DTO (Pydantic)
 ┃ ┃
 ┃ ┗ 📂 media               # Domain: Media
 ┃   ┣ 📂 api
 ┃   ┣ 📂 contracts
 ┃   ┣ 📂 services
 ┃   ┗ 📂 schemas
 ┃
 ┗ 📜 main.py
```

## 📦 Modules (Domains)

Quick access to business domain documentation.

*   **👤 Users Domain**
    *   Registration, Authentication (JWT), Profiles.
*   **🖼️ Media Domain**
    *   File Uploads, CAS Storage, Gallery.
