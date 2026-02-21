# 📜 README

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This `README` file provides essential information and commands for managing database migrations for the Telegram Bot when it operates in "direct" data mode (i.e., when the bot has its own database).

## Purpose

It clarifies that these migrations are only relevant when `BOT_DATA_MODE=direct` and that in `api` mode, the bot interacts with a backend via REST, without direct database access.

## Commands

The `README` outlines key Alembic commands for managing migrations:

*   **Apply all pending migrations:**
    ```bash
    alembic upgrade head
    ```
    This command applies all migration scripts that have not yet been run, bringing the database schema up to the latest version.

*   **Create a new migration after model changes:**
    ```bash
    alembic revision --autogenerate -m "add_user_subscriptions"
    ```
    This command automatically generates a new migration script based on changes detected in the SQLAlchemy models. The `-m` flag allows adding a descriptive message for the migration.

*   **Check current version:**
    ```bash
    alembic current
    ```
    This command displays the current version of the database schema.

## Schema Isolation

The documentation highlights that the bot uses a dedicated PostgreSQL schema named `bot_app` (configurable via the `DB_SCHEMA` environment variable). This approach enables sharing a single database instance (e.g., Neon) with other backend services like Django or FastAPI, while maintaining schema separation.
