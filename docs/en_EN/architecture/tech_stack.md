# 🛠️ Technology Stack & Domains

[⬅️ Back](./README.md) | [🏠 Docs Root](../../README.md)

Unified registry of technologies used in the project, categorized by domain.

## 🌍 Global / Infrastructure

Base technologies used throughout the project.

*   **Containerization:** Docker, Docker Compose.
*   **Web Server:** Nginx (Reverse Proxy, Static files).
*   **Version Control:** Git (GitHub Flow).

## 🔙 Backend Domain (FastAPI)

Server-side logic and API.

*   **Language:** Python 3.11+ (Strict Typing).
*   **Framework:** FastAPI (ASGI, Pydantic v2).
*   **Server:** Uvicorn.
*   **Testing:** Pytest.
*   **Linting:** Ruff, Mypy.

## 💾 Data Domain

Data storage and file management.

*   **Relational DB:** PostgreSQL 15+.
*   **ORM:** SQLAlchemy 2.0 (Async).
*   **Driver:** asyncpg.
*   **Migrations:** Alembic.
*   **File Storage:** Local Filesystem (CAS - Content Addressable Storage).

## 🔐 Security Domain

Security implementation details.

*   **Auth:** OAuth2 (JWT Tokens).
*   **Hashing:** Passlib (Argon2/Bcrypt).
*   **Validation:** Pydantic (Input sanitization).

## 🖼️ Media Domain

Content processing technologies.

*   **Processing:** Pillow (PIL) — resizing, metadata stripping.
*   **Uploads:** Streaming Uploads (FastAPI UploadFile).
